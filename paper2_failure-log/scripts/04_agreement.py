# -*- coding: utf-8 -*-
"""04 분류자 간 일치도 — Cohen's kappa + 불일치 목록(저자 판정용) + 합의 분포."""
import collections, csv, glob, json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "data")
sys.stdout.reconfigure(encoding="utf-8")

valid_n = {json.loads(l)["n"] for l in open(os.path.join(D, "mistakes_anon.jsonl"), encoding="utf-8")}


def load(prefix):
    out, bad = {}, []
    for f in sorted(glob.glob(os.path.join(D, prefix + "_part*.jsonl"))):
        for line in open(f, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            o = json.loads(line)
            (out.__setitem__(o["n"], o) if o["n"] in valid_n else bad.append(o["n"]))
    return out, bad


def kappa(pairs):
    n = len(pairs)
    po = sum(a == b for a, b in pairs) / n
    ca, cb = collections.Counter(a for a, _ in pairs), collections.Counter(b for _, b in pairs)
    pe = sum(ca[k] * cb[k] for k in set(ca) | set(cb)) / (n * n)
    return po, (po - pe) / (1 - pe) if pe < 1 else 1.0


A, badA = load("coding_A"); B, badB = load("coding_B")
common = sorted(set(A) & set(B))
print("분류 항목: A {} · B {} · 공통 {} / 실제 {}".format(len(A), len(B), len(common), len(valid_n)))
print("존재하지 않는 번호를 분류한 경우: A {} · B {}".format(badA or "없음", badB or "없음"))
print("누락: A {} · B {}".format(sorted(valid_n - set(A)) or "없음", sorted(valid_n - set(B)) or "없음"))
for field in ("primary", "detected_by", "recurrence"):
    po, k = kappa([(A[n][field], B[n][field]) for n in common])
    print("  {:<12} 일치율 {:.0%} · Cohen κ {:.2f}".format(field, po, k))

agree = [n for n in common if A[n]["primary"] == B[n]["primary"]]
dist = collections.Counter(A[n]["primary"] for n in agree)
print("\n합의된 주 유형 분포({}건):".format(len(agree)), ", ".join("%s %d" % kv for kv in sorted(dist.items())))
conf = collections.Counter((A[n]["primary"], B[n]["primary"]) for n in common if A[n]["primary"] != B[n]["primary"])
print("불일치 상위 쌍(A→B):", ", ".join("%s→%s %d" % (a, b, c) for (a, b), c in conf.most_common(8)))

with open(os.path.join(D, "coding_disagreements.csv"), "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f); w.writerow(["n", "field", "A(Sonnet)", "B(Opus)", "A_note", "B_note", "adjudicated"])
    for n in common:
        for field in ("primary", "detected_by", "recurrence"):
            if A[n][field] != B[n][field]:
                w.writerow([n, field, A[n][field], B[n][field], A[n].get("note", ""), B[n].get("note", ""), ""])
with open(os.path.join(D, "coding_merged.csv"), "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f); w.writerow(["n", "primary_A", "primary_B", "detected_A", "detected_B", "recur_A", "recur_B"])
    for n in common:
        w.writerow([n, A[n]["primary"], B[n]["primary"], A[n]["detected_by"], B[n]["detected_by"], A[n]["recurrence"], B[n]["recurrence"]])
print("\n불일치 목록 → data/coding_disagreements.csv · 병합표 → data/coding_merged.csv")
