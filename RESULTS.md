# Eval-1 Results — Multi-Session Drift/Conflict

> Reproduce: `python eval1_concurrency.py` → `eval1_results.csv`, `fig5_lost_updates.png` (F5).
> Std-lib only. Real OS-level concurrency (multiprocessing), not a simulation of timing.

## Setup
- Shared artifact seeded empty. **80 events** = 20 items × 4 unique `(id, key)` writes.
  Each `(id, key)` is written exactly once → ground truth is unambiguous: **every event must
  appear in the final merged state.** Any missing event = a **lost update**.
- **K ∈ {2, 4, 8}** concurrent OS processes ("sessions"), events round-robin-assigned, shuffled
  so writers also race on *different* items. Sub-ms jitter widens race windows. **15 trials/cell.**
- Three write disciplines:
  - **A — naive shared-doc (RMW):** read whole JSON → mutate → write whole JSON back, no lock.
    (What an LLM session does when told "edit the dashboard file.")
  - **B — naive append:** append one `{id, key, val}` line in plain `"a"` mode; final state = replay + id-merge.
  - **C — locked append + id-merge (ours):** same append, but guarded by a short-lived OS lock
    (`msvcrt.locking` on Windows / `fcntl.flock` on POSIX). This is the discipline the production helper must follow.

## Results (Windows, 15 trials/cell, 80 events)

| Cond | K | lost (mean) | lost % | lost (max) | corrupt | final-state correct |
|------|---|------------|--------|-----------|---------|---------------------|
| A naive RMW      | 2 | 71.0 | 88.8% | 75 | 0 | 0% |
| A naive RMW      | 4 | 69.5 | 86.8% | 75 | 0 | 0% |
| A naive RMW      | 8 | 72.1 | 90.2% | 79 | 0 | 0% |
| B naive append   | 2 | 2.9  | 3.6%  | 6  | 0 | 13% |
| B naive append   | 4 | 3.8  | 4.8%  | 7  | 0 | 7%  |
| B naive append   | 8 | 2.5  | 3.2%  | 7  | 0 | 7%  |
| **C locked append (ours)** | **2** | **0** | **0%** | **0** | 0 | **100%** |
| **C locked append (ours)** | **4** | **0** | **0%** | **0** | 0 | **100%** |
| **C locked append (ours)** | **8** | **0** | **0%** | **0** | 0 | **100%** |

(Exact numbers vary run-to-run because races are nondeterministic; the *ordering* A ≫ B ≫ C ≈ 0 is stable.)

## Findings
1. **Naive shared-document editing is catastrophic under concurrency.** Whole-file read-modify-write
   loses ~87–90% of updates: each writer's write-back is based on a stale read and clobbers everything
   it didn't see. Final-state correctness is **0%** at every K. This is the default behavior if you tell
   multiple autonomous sessions to "edit the shared file," and it gets worse with more sessions.
2. **Append-only is necessary but not, by itself, sufficient.** Plain `"a"`-mode append already cuts
   loss from ~88% to ~3–5%, but it is **not zero**: on Windows, append is *not atomic* (the C runtime does
   `lseek`-to-EOF then `write`, a race two processes can both win, overwriting one line). So "just append"
   is a platform-dependent claim. **(This is the precise, honest caveat the paper makes — and an artifact
   of the experiment, not an assumption.)**
3. **Append-only + a short-lived lock (+ id-merge replay) is conflict-free.** Condition C loses **0**
   updates and is **100%** correct across K = 2, 4, 8. The lock makes the append atomic; id-merge replay
   makes concurrent writes to the *same* id commute. This is the discipline that makes the system's
   "multi-session writes never conflict" property actually hold.

## Real-artifact tie-in (experiment → fix)
The production dashboard helper (`task-dashboard/log-inquiry.py`) originally used plain `"a"`-mode append
— i.e. **Condition B**. The experiment showed B is *not* truly conflict-free on Windows, so we added the
same short-lived OS lock (Condition C) to the helper's `append()`. Behavior (append-only + id-merge) is
unchanged; only atomicity was added, with a best-effort fallback so a lock failure never drops a write.
The artifact now matches the paper's claim. *(This is the "evaluation found something actionable in the
real system, and we fixed it" loop — a strength for an experience/position paper.)*

## Honest limitations
- Single machine; concurrency is real OS processes but on one host (not a distributed/networked store).
- "Sessions" are writer processes exercising the *logging discipline*, not live LLM calls — by design,
  since the mechanism under test is the write protocol, not the model. A separate experience-report
  covers the human-in-the-loop deployment.
- The lock is advisory and local-filesystem; network filesystems may weaken it. For the single-operator,
  single-host deployment this targets, it is sufficient.

## Files (Eval-1)
- `eval1_concurrency.py` — experiment (A/B/C, scoring, CSV, figure).
- `eval1_results.csv` — machine-readable table.
- `fig5_lost_updates.png` — **F5** (lost updates vs K for A/B/C).

---

# Eval-2 Results — Retrieval mini-eval (F6)

> Reproduce: `python eval2_retrieval.py` → `eval2_results.csv`, `fig6_retrieval.png` (F6).
> Corpus + queries are company-specific and stay LOCAL; only the aggregate numbers below are publishable.
>
> **Update (2026-06-05, post-deployment):** the **"ours" row below is the pre-upgrade snapshot.** The
> recommendation in Finding 2 was subsequently **shipped** — `archive-server.py` now ranks with BM25
> (char-2gram), so a fresh `eval2_retrieval.py` run reports **ours = 81.6% / 85.7%**, identical to the
> "BM25 (char-2gram)" row (the deployed retriever is imported live). The table/figure are retained as the
> before-state that motivated the change.

## Setup
- **Corpus = the live archive (65 articles)**, parsed exactly as the production server does
  (`archive-server.py` imported verbatim; same article boundaries, title, tags, body).
- **Queries = 49 natural-language paraphrases**, each labeled with the gold article id, spanning all 5
  categories (`eval2_queries.tsv`). Codes are partly **phoneticized** (e.g. SE16N→"세16엔", SI→"에스아이",
  0원→"빵원", DCD→"디씨디") so no retriever gets a free literal code match — this deliberately *handicaps*
  the lexical methods, making the comparison conservative for "ours."
- **Retrievers:**
  - **ours** — the *pre-upgrade* passage-lexical scorer (synonym expansion + raw term-count + title/tags ×3), imported live. *(Post-upgrade, the same live import returns the BM25-based ranker — see the update note above.)*
  - **BM25 (word)** — `rank_bm25.BM25Okapi` over regex word tokens.
  - **BM25 (char-2gram)** — same, over Korean-friendly character bigrams (no morph analyzer needed).
  - **dense** — `paraphrase-multilingual-MiniLM-L12-v2`, **passage-chunked** (461 passages, doc score = max
    passage cosine) so long articles are *not* truncated (removes the obvious strawman against dense).
- **Metrics:** Recall@1, Recall@3, MRR@10, mean latency ms/query, plus setup cost.

## Results (65 docs, 49 queries) — pre-upgrade snapshot

| Retriever | Recall@1 | Recall@3 | MRR@10 | latency/query | setup cost |
|-----------|:-------:|:-------:|:------:|:-------------:|------------|
| **BM25 (char-2gram)** | **81.6%** | 85.7% | **0.857** | ~1.2 ms | `rank_bm25`; index ~220 ms |
| BM25 (word) | 75.5% | **87.8%** | 0.829 | ~0.3 ms | `rank_bm25`; index ~90 ms |
| ours (pre-upgrade passage-lexical) | 42.9% | 63.3% | 0.572 | ~40 ms | 0 deps (stdlib) + curated synonym map |
| dense (MiniLM-multi, chunked) | 12.2% | 22.4% | 0.198 | ~88 ms | ~0.5 GB model; ~11 s load + ~55 s encode (CPU) |

(Lexical methods are deterministic; dense numbers are stable across runs.)
*Post-upgrade (2026-06-05): "ours" now equals the BM25 (char-2gram) row — **81.6% / 85.7% / 0.857** — since `search_relevant` was switched to BM25 ranking; rerunning the script reproduces this.*

## Findings
1. **On a small, specialized, Korean-jargon corpus, lexical retrieval dominates an off-the-shelf dense model
   — decisively.** Both BM25 variants beat `MiniLM-multi` by **6–7×** on Recall@1 (81.6% / 75.5% vs 12.2%).
   The gap *survives* passage chunking, so it is not a truncation artifact: a general multilingual sentence
   model simply does not encode SAP Z-codes, internal-order types, and phoneticized abbreviations into useful
   geometry. **Implication for the thesis:** for a single operator maintaining a small specialized KB, a
   near-zero-infrastructure lexical retriever is not a compromise — it is the *better* choice; a competitive
   dense retriever here would require in-domain fine-tuning, which is out of scope for the setting.
2. **The pre-upgrade retriever underperformed plain BM25 (42.9% vs 81.6% Recall@1) — an actionable upgrade the
   eval surfaced, now shipped.** The old scorer used raw term counts + a fixed title ×3 boost; it lacked IDF (so codes that
   appear in many articles add noise) and length normalization (so long articles win unfairly). BM25 supplies
   exactly these. **Resolution (2026-06-05):** `archive-server.py:search_relevant` was switched to a BM25
   ranking (char-2gram tokenization); passage extraction is unchanged. A follow-up measurement gave a second
   finding: **synonym expansion *helps* the old term-count scorer but *hurts* BM25** (putting the curated
   synonyms into the BM25 query dropped R@1 81.6%→67.3%, because common-code synonyms pull unrelated articles
   up — BM25's IDF already handles term importance). So the synonym map was **moved out of ranking and kept
   only for passage extraction** (where it locates the excerpt and cannot distort ranking). Post-change, the
   live-imported "ours" reports **81.6% / 85.7%**, matching BM25 char-2gram. *(Production change to a tracked
   tool → blueprint synced; graceful fallback to the old scorer if `rank_bm25` is absent.)*
3. **Cost/latency:** BM25 is both the most accurate *and* the cheapest at query time (sub-ms to ~1 ms, one
   small dependency, ~0.1–0.2 s index build). Dense costs a ~0.5 GB model, tens of seconds of setup, and is
   the *least* accurate here — a clear "don't" for this corpus class.

## Honest limitations / threats to validity
- **Single small corpus (65 docs), single annotator, 49 queries, one gold id each.** Recall@k on a tiny corpus
  has wide CIs; treat magnitudes, not decimals, as the signal (lexical ≫ off-the-shelf dense; BM25 > ours).
- **The pre-upgrade method included a hand-curated synonym map tuned on this domain.** That was part of the method (cheap,
  human-in-the-loop) but also a generalization caveat — and notably it did *not* lift "ours" above BM25. *(Post-upgrade the
  synonym map is retained only for passage extraction, not ranking — it measurably hurt BM25 ranking; see Finding 2.)*
- **Only one small dense model, off-the-shelf, no fine-tuning.** A domain-adapted or larger dense model would
  do better; the claim is specifically about the *low-cost, no-training* dense option a solo maintainer would reach for.
- **Phoneticized-code queries** make the set harder than typical (and harder on lexical than on a semantic model),
  so the lexical win is, if anything, understated.

## Files (Eval-2)
- `eval2_retrieval.py` — experiment (imports the live retriever; BM25 ×2; chunked dense; scoring; CSV; figure).
- `eval2_queries.tsv` — 49 labeled queries (LOCAL only).
- `eval2_results.csv` — machine-readable table.
- `fig6_retrieval.png` — **F6** (Recall@1/@3 per retriever).
