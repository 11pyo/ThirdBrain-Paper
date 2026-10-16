# -*- coding: utf-8 -*-
"""02 익명화 — 사람·회사·고객사·문서번호·사내 코드를 치환하고 누출을 검사한다.

사용
  python 02_anonymize.py --candidates   고유명사 후보를 뽑아 data_private/anon_candidates.txt 로(사전 작성용)
  python 02_anonymize.py                data_private/anon_dict.json 으로 치환 → data/mistakes_anon.jsonl + 누출 검사
사전 형식: {"people": [...], "orgs": [...], "keep": [...]}  (사전 자체가 민감 → 비공개 폴더)
"""
import collections, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data_private", "mistakes_raw.jsonl")
DICT = os.path.join(ROOT, "data_private", "anon_dict.json")
OUT = os.path.join(ROOT, "data", "mistakes_anon.jsonl")
TITLE = r"(?:매니저|팀장|사원|부장|과장|대리|차장|본부장|실장|책임|선임|주임|님|K)"

P_PERSON = re.compile(r"([가-힣]{2,4})\s?" + TITLE)
P_PERSON2 = re.compile(r"([가-힣]{3})·")
P_ORG = re.compile(r"\(주\)\s?([가-힣A-Za-z0-9]+)|([가-힣A-Za-z0-9]{2,})\s?\(주\)|㈜\s?([가-힣A-Za-z0-9]+)|주식회사\s?([가-힣A-Za-z0-9]+)")
P_ORG2 = re.compile(r"([가-힣]{2,10}(?:시스템즈|정보통신|네트웍스|인포스?|솔루션|코리아|전자|은행|증권|거래소|카드|보험|물산|제강|씨엠|홀딩스|엔시스|인프라|큐엔씨|인터내셔널|데이타|데이터게이트))")

# 구조 규칙(사전과 무관하게 항상 적용). 순서 중요 — 긴 패턴 먼저.
RULES = [
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"), "[이메일]"),
    (re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"), "[IP]"),
    (re.compile(r"\b0\d{1,2}-\d{3,4}-\d{4}\b"), "[전화]"),
    (re.compile(r"\b(?:SI|MA|SP|SM|SR|DE|CO|JA|BA)\d{8}\b"), "[품의번호]"),
    (re.compile(r"\bINQ-\d{6}-\d{6}\b"), "[문의번호]"),
    (re.compile(r"\b[A-Z]{3}K9\d{5}\b"), "[전송요청번호]"),
    (re.compile(r"\bF20\d{9}\b"), "[납품번호]"),
    (re.compile(r"\b(?:3000|5000|4900|2607|2605)\d{6,9}\b"), "[문서번호]"),
    (re.compile(r"\b[Zz][A-Za-z0-9_]{3,}\b"), "[사내오브젝트]"),       # 사내 개발 코드(Z 네임스페이스)
    # 개발계·운영계 구분은 실패의 핵심 정보 — 뭉치지 않고 역할로 남긴다
    (re.compile(r"\bDSD\s?100\b"), "[개발계-개발]"),
    (re.compile(r"\bDSD\s?120\b"), "[개발계-테스트]"),
    (re.compile(r"\bDSD\s?110\b"), "[개발계-설정]"),
    (re.compile(r"\bDSD\d{0,3}\b"), "[개발계]"),
    (re.compile(r"\bDSP\d{0,3}\b"), "[운영계]"),
    (re.compile(r"(?i)\[회사명\]|\bCORP\b|[가-힣]*그룹사"), "[그룹사]"),
    (re.compile(r"\b(?:VENDOR_A|VENDOR_B|IBM|LG|SK|KT)\b"), "[벤더]"),
]


def load():
    return [json.loads(l) for l in open(RAW, encoding="utf-8")]


def candidates(rows):
    c = collections.Counter()
    for r in rows:
        t = r["title"] + "\n" + r["body"]
        for m in P_PERSON.finditer(t):
            c[("사람?", m.group(1))] += 1
        for m in P_PERSON2.finditer(t):
            c[("사람?", m.group(1))] += 1
        for m in P_ORG.finditer(t):
            c[("조직?", next(g for g in m.groups() if g))] += 1
        for m in P_ORG2.finditer(t):
            c[("조직?", m.group(1))] += 1
    path = os.path.join(ROOT, "data_private", "anon_candidates.txt")
    with open(path, "w", encoding="utf-8") as f:
        for (k, w), n in c.most_common():
            f.write("{}\t{}\t{}\n".format(k, w, n))
    return path, c


def apply(text, people_map, org_map, keep):
    for w in sorted(org_map, key=len, reverse=True):
        text = text.replace(w, org_map[w])
    for w in sorted(people_map, key=len, reverse=True):   # 뒤에 조사가 붙어도(「[작성자]가」) 치환 — 실명 3글자는 충분히 특이하다
        text = text.replace(w, people_map[w])
    for pat, rep in RULES:
        text = pat.sub(lambda m: m.group(0) if m.group(0) in keep else rep, text)
    return text


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    rows = load()
    if "--candidates" in sys.argv:
        path, c = candidates(rows)
        print("후보 {}개 → {}".format(len(c), path))
        return
    d = json.load(open(DICT, encoding="utf-8"))
    keep = set(d.get("keep", []))
    people_map = {w: "[사람{}]".format(chr(65 + i) if i < 26 else i) for i, w in enumerate(d["people"])}
    org_map = {w: "[조직{}]".format(i + 1) for i, w in enumerate(d["orgs"])}
    out = []
    for r in rows:
        out.append({"n": r["n"], "domain": r["domain"],
                    "title": apply(r["title"], people_map, org_map, keep),
                    "body": apply(r["body"], people_map, org_map, keep)})
    with open(OUT, "w", encoding="utf-8") as f:
        for o in out:
            f.write(json.dumps(o, ensure_ascii=False) + "\n")
    # 누출 검사: 사전 단어·구조 패턴이 결과에 남았나
    blob = "\n".join(o["title"] + o["body"] for o in out)
    leaks = [w for w in list(people_map) + list(org_map) if w in blob]
    for pat, _ in RULES:
        leaks += [m.group(0) for m in pat.finditer(blob) if m.group(0) not in keep]
    # 사전에 없는 실명 탐지: 「세 글자 + 직함」만(「님·K」까지 보면 일반어가 대량으로 걸린다). 부서명은 제외.
    strict = re.compile(r"([가-힣]{3})\s?(?:매니저|팀장|사원|부장|과장|대리|차장|본부장|실장|선임|책임)")
    leaks += [m.group(1) for m in strict.finditer(blob)
              if m.group(1) not in keep and not re.search(r"(?:팀|부|실|파트|본부|센터|담당|업무|현업)$", m.group(1))]
    print("익명화 {}건 → {}".format(len(out), OUT))
    print("누출 의심 {}건: {}".format(len(leaks), ", ".join(sorted(set(leaks))[:60])))
    return 1 if leaks else 0


if __name__ == "__main__":
    sys.exit(main())
