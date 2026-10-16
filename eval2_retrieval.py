# -*- coding: utf-8 -*-
"""
Eval-2 (F6) — Retrieval mini-eval on the real archive corpus.

Compares the deployed passage-lexical retriever (imported verbatim from
archive-server.py: synonym expansion + title x3 boost + substring match)
against BM25 (word tokens; char-2gram) and a small multilingual dense model
(sentence-transformers paraphrase-multilingual-MiniLM-L12-v2).

Corpus  = the live archive.html articles (65), parsed exactly as the server does.
Queries = eval2_queries.tsv (natural-language paraphrases -> gold article id;
          codes are partly phoneticized so no retriever gets a free literal match).

Metrics : recall@1, recall@3, MRR@10, mean latency ms/query, + setup cost.

PRIVACY: corpus/queries are company-specific and stay LOCAL. Only AGGREGATE
metrics (this script's table/figure) are publishable.
"""
import os, re, sys, io, csv, time, json, importlib.util
from collections import defaultdict

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
ARCHIVE_DIR = r"C:\Users\DKSYSTEMS\Documents\SAP SD AI Indexable Archive"
SERVER_PY = os.path.join(ARCHIVE_DIR, "archive-server.py")

# ---------- load the real retriever + corpus ----------
def load_server():
    spec = importlib.util.spec_from_file_location("arsv", SERVER_PY)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    m.load()
    return m

def build_corpus(m):
    docs = []  # {id, title, text}
    for a in m._arts:
        body = m.norm(m.strip_tags(m._html[a["pos"]:a["end"]]))
        docs.append({"id": a["id"],
                     "title": a["title"],
                     "tags": a.get("tags", ""),
                     "text": (a["title"] + " " + a.get("tags", "") + " " + body)})
    return docs

# ---------- retriever 1: ours (deployed retriever, called live) ----------
def rank_ours(m, query, top_n=10):
    # 배포 검색기와 100% 동일 경로로 평가: archive-server.py 의 BM25 랭킹을 직접 호출.
    # (과거엔 스코어링을 여기서 재구현했으나, 이제 서버 변경이 자동 반영되도록 rank_article_ids 에 위임.)
    return m.rank_article_ids(query, top_n)

# ---------- retriever 2/3: BM25 (word ; char-2gram) ----------
def tok_word(s):
    return [w.lower() for w in re.findall(r"[A-Za-z가-힣][A-Za-z가-힣0-9_]{1,}", s)]

def tok_char2(s):
    s = re.sub(r"\s+", "", s.lower())
    return [s[i:i+2] for i in range(len(s) - 1)] if len(s) >= 2 else [s]

def make_bm25(docs, tok):
    from rank_bm25 import BM25Okapi
    t0 = time.perf_counter()
    corpus_tok = [tok(d["text"]) for d in docs]
    bm = BM25Okapi(corpus_tok)
    build_ms = (time.perf_counter() - t0) * 1000
    def rank(query, top_n=10):
        sc = bm.get_scores(tok(query))
        order = sorted(range(len(docs)), key=lambda i: -sc[i])
        return [docs[i]["id"] for i in order[:top_n]]
    return rank, build_ms

# ---------- retriever 4: dense (passage-chunked so long docs aren't truncated) ----------
def _passages(text, win=80, stride=60):
    toks = text.split()
    if len(toks) <= win:
        return [text]
    out = []
    for i in range(0, len(toks), stride):
        out.append(" ".join(toks[i:i+win]))
        if i + win >= len(toks):
            break
    return out

def make_dense(docs):
    from sentence_transformers import SentenceTransformer
    import numpy as np
    t0 = time.perf_counter()
    model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    load_ms = (time.perf_counter() - t0) * 1000
    # chunk each doc into passages; doc score = max passage similarity (standard for long docs)
    passages, owner = [], []
    for di, d in enumerate(docs):
        for p in _passages(d["text"]):
            passages.append(p); owner.append(di)
    t1 = time.perf_counter()
    emb = np.asarray(model.encode(passages, normalize_embeddings=True, show_progress_bar=False))
    build_ms = (time.perf_counter() - t1) * 1000
    owner = np.asarray(owner)
    def rank(query, top_n=10):
        q = model.encode([query], normalize_embeddings=True, show_progress_bar=False)[0]
        psims = emb @ q
        doc_sim = np.full(len(docs), -1e9)
        for pi, di in enumerate(owner):
            if psims[pi] > doc_sim[di]:
                doc_sim[di] = psims[pi]
        order = sorted(range(len(docs)), key=lambda i: -doc_sim[i])
        return [docs[i]["id"] for i in order[:top_n]]
    return rank, load_ms, build_ms, len(passages)

# ---------- scoring ----------
def evaluate(rank_fn, queries):
    r1 = r3 = mrr = 0
    lat = []
    for q, gold in queries:
        t0 = time.perf_counter()
        ranked = rank_fn(q, top_n=10)
        lat.append((time.perf_counter() - t0) * 1000)
        if ranked[:1] == [gold]: r1 += 1
        if gold in ranked[:3]:   r3 += 1
        if gold in ranked[:10]:  mrr += 1.0 / (ranked.index(gold) + 1)
    n = len(queries)
    return {"recall@1": r1/n, "recall@3": r3/n, "mrr@10": mrr/n,
            "lat_ms": sum(lat)/len(lat), "n": n}

def main():
    queries = []
    with open(os.path.join(HERE, "eval2_queries.tsv"), encoding="utf-8") as f:
        rd = csv.DictReader(f, delimiter="\t")
        for row in rd:
            queries.append((row["query"].strip(), row["gold_id"].strip()))
    m = load_server()
    docs = build_corpus(m)
    ids = {d["id"] for d in docs}
    missing = [g for _, g in queries if g not in ids]
    print(f"corpus={len(docs)} articles | queries={len(queries)} | gold-not-in-corpus={missing}")

    methods = {}
    methods["ours (deployed: BM25 c2g)"] = (lambda q, top_n=10: rank_ours(m, q, top_n),
                                         {"deps": "rank_bm25", "setup": "BM25 char-2gram (server live)"})

    bm_w, bw_ms = make_bm25(docs, tok_word)
    methods["BM25 (word)"] = (bm_w, {"deps": "rank_bm25", "setup": f"index {bw_ms:.0f}ms"})
    bm_c, bc_ms = make_bm25(docs, tok_char2)
    methods["BM25 (char-2gram)"] = (bm_c, {"deps": "rank_bm25", "setup": f"index {bc_ms:.0f}ms"})

    try:
        d_rank, d_load_ms, d_build_ms, n_pass = make_dense(docs)
        methods["dense (MiniLM-multi, chunked)"] = (d_rank, {"deps": "sentence-transformers+torch (~0.5GB model)",
                                                    "setup": f"load {d_load_ms:.0f}ms + encode {n_pass}p {d_build_ms:.0f}ms"})
    except Exception as e:
        print("dense unavailable (offline/download failed):", repr(e)[:160])

    rows = []
    print(f"\n{'method':<26}{'R@1':>7}{'R@3':>7}{'MRR@10':>9}{'lat(ms)':>10}   setup")
    for name, (fn, meta) in methods.items():
        r = evaluate(fn, queries)
        rows.append({"method": name, **{k: round(v, 4) for k, v in r.items() if k != "n"},
                     "n": r["n"], "deps": meta["deps"], "setup": meta["setup"]})
        print(f"{name:<26}{r['recall@1']*100:>6.1f}%{r['recall@3']*100:>6.1f}%{r['mrr@10']:>9.3f}{r['lat_ms']:>10.2f}   {meta['deps']} | {meta['setup']}")

    out = os.path.join(HERE, "eval2_results.csv")
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    print("CSV ->", out)

    try:
        import matplotlib; matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
        names = [r["method"] for r in rows]
        x = np.arange(len(names)); wdt = 0.38
        plt.figure(figsize=(7.2, 3.6))
        plt.bar(x - wdt/2, [r["recall@1"]*100 for r in rows], wdt, label="Recall@1", color="#2563eb")
        plt.bar(x + wdt/2, [r["recall@3"]*100 for r in rows], wdt, label="Recall@3", color="#60a5fa")
        plt.xticks(x, names, rotation=18, ha="right", fontsize=8)
        plt.ylabel("hit rate (%)"); plt.ylim(0, 100)
        plt.title(f"Retrieval hit rate on real archive ({len(docs)} docs, {len(queries)} queries)")
        plt.legend(); plt.grid(axis="y", alpha=.3); plt.tight_layout()
        fig = os.path.join(HERE, "fig6_retrieval.png")
        plt.savefig(fig, dpi=140); print("FIG ->", fig)
    except Exception as e:
        print("figure skipped:", repr(e)[:160])

if __name__ == "__main__":
    main()
