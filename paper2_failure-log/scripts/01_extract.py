# -*- coding: utf-8 -*-
"""01 추출 — 실수 로그 항목 분리 + 작성 시각·작성 모델·주 모델 시기 부여 (원천은 읽기만).

출력
  data_private/mistakes_raw.jsonl  항목 원문 포함(비공개)
  data/mistakes_meta.csv           원문 없는 메타(공개 가능)
  data/model_eras.csv              날짜별 주 모델(공개 가능)
"""
import collections, csv, datetime, glob, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TR = r"C:\Users\DKSYSTEMS\.claude\projects\c--Users-DKSYSTEMS-Documents-SAP-SD-AI-Indexable-Archive"
MEM = os.path.join(TR, "memory")
# 제목 형식이 여러 가지다: 「실수 14 —」「실수 182 (구 60) —」「실수 176 (구164) —」「실수 119 (2026-09-07 …」
HEAD = re.compile(r"^(?:\*\*|#{2,4} )(?:실수 (\d{1,3})(?=\D)|(\d{1,3})\. )(?:\s*\((?:구\s*(\d{1,3}))?[^)]*\))?")
# 「### 180. …」처럼 「실수」 없이 번호만 쓴 제목도 있다(2026-09-29 분류자 A가 발견 — 추출기가 179번 본문에 붙였었다)
DATE = re.compile(r"20\d\d-\d\d-\d\d")
REC = re.compile(r"재발|번째|또 |반복|연속|다시 같은")
KST = datetime.timedelta(hours=9)


def kst_date(ts):
    return (datetime.datetime.fromisoformat(ts.replace("Z", "+00:00")) + KST).date().isoformat()


def load_entries():
    out = []
    for f in sorted(glob.glob(os.path.join(MEM, "feedback_pitfalls_*.md"))):
        domain = os.path.basename(f)[len("feedback_pitfalls_"):-3]
        cur = None
        for line in open(f, encoding="utf-8"):
            m = HEAD.match(line)
            if m:
                if cur:
                    out.append(cur)
                cur = {"n": int(m.group(1) or m.group(2)), "old_n": int(m.group(3)) if m.group(3) else None,
                       "domain": domain, "title": line.strip(), "body": ""}
                continue
            if cur is not None:
                if re.match(r"^#{1,2} [^실]", line):      # 다음 대단원 제목이면 항목 끝
                    out.append(cur); cur = None
                else:
                    cur["body"] += line
        if cur:
            out.append(cur)
    return out


def scan_transcripts():
    per_day = collections.defaultdict(collections.Counter)
    first = {}
    pat = re.compile(r"실수 (\d{1,3})(?: \(구 \d+\))? —")
    for p in glob.glob(os.path.join(TR, "*.jsonl")):
        for line in open(p, encoding="utf-8", errors="replace"):
            if '"assistant"' not in line:
                continue
            try:
                o = json.loads(line)
            except ValueError:
                continue
            if o.get("type") != "assistant" or o.get("isSidechain"):
                continue
            msg = o.get("message") or {}
            model = re.sub(r"-\d{8}$", "", msg.get("model") or "")
            ts = o.get("timestamp") or ""
            if not model or model == "<synthetic>" or not ts:
                continue
            per_day[kst_date(ts)][model] += 1
            if "실수 " not in line or '"tool_use"' not in line:
                continue
            for b in msg.get("content") or []:
                if not isinstance(b, dict) or b.get("type") != "tool_use":
                    continue
                inp = b.get("input") or {}
                if "pitfall" not in json.dumps(inp, ensure_ascii=False):
                    continue
                blob = " ".join(str(inp.get(k, "")) for k in ("content", "new_string", "command"))
                for m in pat.finditer(blob):
                    n = int(m.group(1))
                    if n not in first or ts < first[n][0]:
                        first[n] = (ts, model)
    return per_day, first


def main():
    entries = load_entries()
    per_day, first = scan_transcripts()
    dom = {d: c.most_common(1)[0][0] for d, c in per_day.items()}
    os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)
    os.makedirs(os.path.join(ROOT, "data_private"), exist_ok=True)

    with open(os.path.join(ROOT, "data", "model_eras.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f); w.writerow(["date_kst", "dominant_model", "assistant_msgs_total", "models"])
        for d in sorted(per_day):
            c = per_day[d]; w.writerow([d, dom[d], sum(c.values()), ";".join("%s:%d" % kv for kv in c.most_common())])

    rows = []
    for e in entries:
        head_dates = DATE.findall(e["title"]); body_dates = DATE.findall(e["body"])
        key = e["n"] if not e["old_n"] else None          # 재번호 항목은 옛 번호가 다른 항목과 겹쳐 전사 추적 제외
        wt = first.get(key) if key else None
        written = kst_date(wt[0]) if wt else None
        incident = (head_dates or body_dates or [None])[0]
        basis = "transcript" if wt else ("heading_date" if head_dates else ("body_date" if body_dates else "none"))
        date_for_era = written or incident
        e.update({
            "written_kst": written, "writer_model": wt[1] if wt else None,
            "incident_date": incident, "date_basis": basis,
            "era_model": dom.get(date_for_era) if date_for_era else None,
            "recurrence_flag": bool(REC.search(e["title"] + e["body"][:600])),
            "refs": sorted({int(x) for x in re.findall(r"실수 (\d{1,3})", e["body"]) if int(x) != e["n"]}),
            "n_chars": len(e["body"]),
        })
        rows.append(e)
    rows.sort(key=lambda r: r["n"])

    with open(os.path.join(ROOT, "data_private", "mistakes_raw.jsonl"), "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    cols = ["n", "old_n", "domain", "written_kst", "writer_model", "incident_date", "date_basis", "era_model", "recurrence_flag", "refs", "n_chars"]
    with open(os.path.join(ROOT, "data", "mistakes_meta.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f); w.writerow(cols)
        for r in rows:
            w.writerow([";".join(map(str, r[c])) if isinstance(r[c], list) else r[c] for c in cols])

    sys.stdout.reconfigure(encoding="utf-8")
    ns = [r["n"] for r in rows]
    print("항목 {}건 · 번호 중복 {} · 빠진 번호 {}".format(len(rows), sorted({n for n in ns if ns.count(n) > 1}),
                                                  sorted(set(range(1, max(ns) + 1)) - set(ns))))
    print("날짜 근거:", dict(collections.Counter(r["date_basis"] for r in rows)))
    print("시기 모델 부여:", sum(1 for r in rows if r["era_model"]), "/", len(rows))
    print("작성 모델:", dict(collections.Counter(r["writer_model"] for r in rows if r["writer_model"])))


if __name__ == "__main__":
    main()
