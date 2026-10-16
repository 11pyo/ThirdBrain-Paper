# -*- coding: utf-8 -*-
"""05 기술 통계(초벌) — 합의 분류 × 작성 모델 × 시기. RQ2(모델 교차 재발)·RQ4(발견 주체)."""
import collections, csv, glob, json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "data")
sys.stdout.reconfigure(encoding="utf-8")

meta = {int(r["n"]): r for r in csv.DictReader(open(os.path.join(D, "mistakes_meta.csv"), encoding="utf-8-sig"))}


def load(prefix):
    out = {}
    for f in sorted(glob.glob(os.path.join(D, prefix + "_part*.jsonl"))):
        for line in open(f, encoding="utf-8"):
            if line.strip():
                o = json.loads(line); out[o["n"]] = o
    return out


A, B = load("coding_A"), load("coding_B")
agreed = {n: A[n] for n in A if n in B and A[n]["primary"] == B[n]["primary"]}
NAMES = {"F1": "출처·딱지", "F2": "단위·표기", "F3": "검증 생략", "F4": "근거 없는 확신", "F5": "의도 무시", "F6": "관문 건너뜀",
         "F7": "범위 이탈", "F8": "기록 결함", "F9": "소통", "F10": "도구 조작", "F11": "기타"}

print("## RQ2 — 합의된 유형별: 건수 · 작성 모델 종류 · 시기 모델 종류 · 등장한 달")
rows = []
for code in sorted({a["primary"] for a in agreed.values()}, key=lambda c: int(c[1:])):
    ns = [n for n, a in agreed.items() if a["primary"] == code]
    writers = {meta[n]["writer_model"] for n in ns if meta.get(n, {}).get("writer_model")}
    eras = {meta[n]["era_model"] for n in ns if meta.get(n, {}).get("era_model")}
    months = sorted({(meta[n]["written_kst"] or meta[n]["incident_date"] or "")[:7] for n in ns} - {""})
    rows.append((code, len(ns), len(writers), len(eras), months))
    print("  {:<4}{:<10} {:>3}건 · 작성모델 {}종 · 시기모델 {}종 · {}".format(code, NAMES[code], len(ns), len(writers), len(eras), " ".join(months)))
multi = [r for r in rows if r[3] >= 3]
print("  → 시기 모델 3종 이상에 걸쳐 나타난 유형: {}개 ({})".format(len(multi), ", ".join(r[0] for r in multi)))

print("\n## RQ4 — 발견 주체(두 분류자 일치 건만)")
det = collections.Counter(A[n]["detected_by"] for n in A if n in B and A[n]["detected_by"] == B[n]["detected_by"])
tot = sum(det.values())
print("  " + " · ".join("{} {} ({:.0%})".format(k, v, v / tot) for k, v in det.most_common()))

print("\n## 재발 표기(두 분류자 모두 yes) — 시기 모델별")
rec = collections.Counter(meta[n]["era_model"] or "(6/9 이전)" for n in A if n in B and A[n]["recurrence"] == B[n]["recurrence"] == "yes")
print("  " + " · ".join("%s %d" % kv for kv in rec.most_common()))

print("\n## 월별 기록 건수(작성일, 없으면 사건일)")
mon = collections.Counter((meta[n]["written_kst"] or meta[n]["incident_date"] or "????")[:7] for n in meta)
print("  " + " · ".join("%s %d" % kv for kv in sorted(mon.items())))
