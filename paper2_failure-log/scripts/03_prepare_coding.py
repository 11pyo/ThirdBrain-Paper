# -*- coding: utf-8 -*-
"""03 분류 입력 준비 — 익명화 항목을 사람이 읽기 좋은 묶음 파일로 나눈다(본문은 앞·뒤를 남겨 길이 제한)."""
import json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "data", "mistakes_anon.jsonl")
OUT = os.path.join(ROOT, "data", "coding_batches")
HEAD_CH, TAIL_CH, PER = 1400, 500, 47   # 4묶음


def clip(body):
    b = body.strip()
    return b if len(b) <= HEAD_CH + TAIL_CH else b[:HEAD_CH] + "\n…(중략)…\n" + b[-TAIL_CH:]


rows = [json.loads(l) for l in open(SRC, encoding="utf-8")]
rows.sort(key=lambda r: r["n"])
os.makedirs(OUT, exist_ok=True)
for i in range(0, len(rows), PER):
    part = rows[i:i + PER]
    path = os.path.join(OUT, "batch_%02d.md" % (i // PER + 1))
    with open(path, "w", encoding="utf-8") as f:
        f.write("# 분류 대상 묶음 — 실수 {}~{} ({}건)\n\n".format(part[0]["n"], part[-1]["n"], len(part)))
        for r in part:
            f.write("---\n## n={} · 영역={}\n{}\n\n{}\n\n".format(r["n"], r["domain"], r["title"], clip(r["body"])))
sys.stdout.reconfigure(encoding="utf-8")
for fn in sorted(os.listdir(OUT)):
    print(fn, os.path.getsize(os.path.join(OUT, fn)), "bytes")
