# Paper Outline — "AI-Maintained Knowledge Artifacts" (Third-Party-Brain)

> 형식: **경험/포지션 페이퍼, 2~4p.** 목표 게재처(ROI 순): arXiv 프리프린트 + Zenodo DOI → (선택) 에이전트 워크숍 / IEEE Software 실무 아티클 / ICSE-SEIP.
> ⚠️ 인용은 *기억 기반 후보* — 제출 전 정확한 서지·연도 반드시 확인. 배포 도메인은 익명화("an enterprise ERP-operations domain").
> 상태: DRAFT(비공개, 미푸시). 원본 사례 = Third-Party-Brain(github.com/11pyo/Third-Party-Brain).

---

## 0. 제목 후보
- **(주)** *AI-Maintained Knowledge Artifacts: Invariants, Conflict-Free Logs, and Dual-Register Docs for Drift-Free Multi-Session Maintenance*
- (부) *A zero-infrastructure operational knowledge base that autonomous LLM sessions can keep current without drift or write conflicts*
- (국문) *AI가 유지보수하는 지식 아티팩트 — 다중 세션 드리프트·충돌 없는 운영 지식베이스의 규율*

## 1. 한 줄 테제 (Thesis)
> **세 가지 작은 저작 규율** — (1) 사람용·에이전트용 **이중 레지스터 문서**, (2) **명시적·검증가능 불변식 + 강제 동기화**, (3) **추가전용·id 병합 로그를 조정 프리미티브로** — 이 있으면, **여러 자율 LLM 세션이 단일 파일 운영 지식베이스를 시간에 걸쳐 드리프트·쓰기충돌 없이 유지**할 수 있다. 서버·DB 0, 오프라인·무API 검색 가능.

## 2. 기여 (Contributions) — 3개
- **C1 (현상)**: 실제 다중 세션 배포에서 관찰한 **AI 유지보수 실패 모드 분류** — ① 정의 드리프트/불일치 ② 다중 세션 쓰기 충돌 ③ 긴 글 컨텍스트 절단 ④ 인수인계 공백.
- **C2 (메커니즘)**: 이를 완화하는 **재사용 가능·공개 방법론** — 이중문서+불변식+동기화 / 충돌없는 append-only id-merge 로그 / 패시지 중심 검색 + 인테이크 정의불일치 검사. (오픈소스 블루프린트로 공개)
- **C3 (평가)**: **경량 평가** — 다중 세션 드리프트/충돌 통제 실험(주) + 6주 단일 운영자 배포 경험보고(버스팩터-1 인수인계)(보조).

## 3. 논문 구조 (섹션)
1. **Introduction** — 버스팩터-1 문제 / agentic 유지보수의 부상 / SME·개인 운영엔 무거운 RAG·DB가 과함 / 테제·기여.
2. **Background & Related Work** — §6 포지셔닝.
3. **The Artifact & Setting** — 단일 HTML KB + 도구3 + 운영 대시보드; 익명 배포(엔터프라이즈 ERP 운영, 운영자 1, ~수주, 아티클 ~수십).
4. **Failure Modes Observed** — 위 4종, 각 실제 사례(익명).
5. **Disciplines / Mechanisms** — (a) 이중문서+불변식(INV1~9, INV-OL1~4)+강제 동기화 (b) 충돌없는 append-only id-merge 로그 (c) 패시지 검색 + 정의불일치 인테이크 검사 (d) read-structure/guide-prod 안전모델(간략).
6. **Evaluation** — Eval-1(드리프트/충돌) + 경험보고 지표.
7. **Discussion & Limitations** — N=1 도메인·단일 운영자·외적타당성 / 스케일 임계점에서의 한계 / 보안·공개수준.
8. **Conclusion** — 가벼운 규율로 "AI가 유지하는 지식 아티팩트"가 실용 가능; 후속(다도메인·다사용자).

## 4. 초록 초안 (~150 words, EN)
> Operational knowledge often lives in one person's head; when they leave, work stalls (bus factor 1). We report on a *zero-infrastructure, single-file* operational knowledge base — one HTML file plus small local tools and a server-less dashboard — designed so that **autonomous LLM sessions can maintain it over time**. We identify four failure modes that appear when agents (across sessions) edit a shared knowledge artifact: definition drift, multi-session write conflicts, long-document context truncation, and handover gaps. We present three lightweight disciplines that mitigate them: **dual-register documentation** (human + agent) with **explicit, checkable invariants and mandatory synchronization**; an **append-only, id-merge log** used as a coordination primitive so concurrent sessions never conflict; and **passage-centered retrieval** with an intake-time definition-divergence check. A controlled multi-session experiment shows that a naive shared-document baseline loses ~88% of concurrent updates, that plain appending is necessary but not sufficient (it remains non-atomic on some platforms), and that **append-only with atomic appends plus id-merge replay eliminates lost updates entirely** (0% loss, 100% final-state correctness at 2–8 concurrent writers); the experiment also surfaced and fixed a latent non-atomicity in the deployed helper. On the live corpus, a near-zero-infrastructure lexical retriever (BM25) outperforms an off-the-shelf small multilingual dense model by 6–7× in Recall@1 (82% vs 12%), confirming that for a small, specialized knowledge base lexical retrieval is the better, not merely cheaper, choice. The methodology is released as open source.

## 5. 선행연구 후보 (5~6 묶음) — *서지 확인 필요*
1. **PKM / Second Brain / docs-as-code** — Obsidian·Roam·Logseq; Tiago Forte, *Building a Second Brain*(2022); "docs as code"(Write the Docs). → *차별점: AI 유지보수 규율을 더함.*
2. **RAG & 어휘 baseline** — Lewis et al., *Retrieval-Augmented Generation*(NeurIPS 2020); Karpukhin et al., *DPR*(EMNLP 2020); "BM25/어휘 baseline이 의외로 경쟁력" 계열(예: Thakur et al., *BEIR* 2021). → *차별점: 소규모 코퍼스용 무인프라·오프라인 어휘+패시지 RAG-lite.*
3. **LLM 에이전트 메모리** — Packer et al., *MemGPT*(2023); Park et al., *Generative Agents*(UIST 2023); Shinn et al., *Reflexion*(2023); 에이전트 메모리 서베이. → *차별점: 외부·사람가독·파일기반·에이전트가 유지하는 공유 메모리.*
4. **충돌없는 데이터 / 조정** — Shapiro et al., *CRDTs*(2011); event sourcing / append-only log(Kleppmann, *DDIA* 2017). → *차별점: 최소 append-only id-merge 로그를 다중 LLM 세션 조정 프리미티브로(응용 신규성).*
5. **버스팩터 / 지식이전 (SE)** — Avelino et al., *truck factor*(ICPC 2016); Nonaka SECI(암묵→형식지). → *차별점: AI 보조 인수인계 아티팩트.*
6. **에이전트용 문서 / AI-readable 인터페이스** — llms.txt 제안; README/AGENTS.md/CLAUDE.md 관행; (자매작) 저자의 AFRM/AINavManifest(웹 상호작용측). → *차별점: 유지보수자가 AI인 경우의 이중 레지스터 문서·불변식.*

> 인용 묶음별로 "그들은 X, 우리는 Y" 한 줄씩 → Related Work 한 단락. 6묶음 중 4~5개만 추려 2~4p에 맞춤.

## 6. ⭐ Eval-1 설계 — 다중 세션 드리프트/충돌 (주 평가) ✅ 실행 완료
> 구현=`eval1_concurrency.py`, 결과=`RESULTS.md`/`eval1_results.csv`/`fig5_lost_updates.png`(F5). std-lib only, 실제 OS 동시성(multiprocessing).
- **가설(H)**: append-only + id-merge + **원자적 append**가, naive 공유문서 직접편집 대비 **lost update·충돌을 0으로** 만든다.
- **셋업**: 빈 공유 아티팩트에 80 이벤트(20 item × 4 unique (id,key)). 동시 프로세스 K개(K∈{2,4,8})가 라운드로빈+셔플로 동시 기록, 15 trial/cell, sub-ms jitter.
- **조건 (3개)**:
  - (A) baseline: 공유 JSON 직접 read-modify-write(무락, last-writer-wins).
  - (B) naive append: 평범한 `"a"` 모드 append + id-merge 리플레이.
  - (C) **ours**: append + 짧은 OS 락(msvcrt/fcntl) → 원자적 append + id-merge.
- **결과**: A=**~88% lost**(정확도 0%) ≫ B=**~3–5% lost**(평범한 append는 Windows에서 비원자적이라 0이 아님) ≫ **C=0% lost, 정확도 100%(K=2,4,8 전부)**.
- **핵심 발견(정직한 정밀화)**: "그냥 append하면 충돌없음"은 **플랫폼 의존**. 진짜 충돌-free 주장에는 **원자적 append(락/`O_APPEND`)가 필수**. 이건 가정이 아니라 *실험 산물*.
- **실아티팩트 연결(실험→수정)**: 실제 헬퍼 `log-inquiry.py`가 원래 조건 B(무락 append)였음 → 실험이 잠재 결함을 짚어내, 동일 락(조건 C)을 `append()`에 추가(동작 불변, 원자성만 추가, 락 실패시 fallback). **아티팩트가 논문 주장과 일치하게 됨.**
- **지표**: ① lost updates ② 손상상태 ③ 최종상태 정확도 ④ (KB측, 향후) 인테이크 정의불일치 검출.
- **정직 한계**: 단일머신·로컬FS 락·시뮬 동시성(실사용자 연구 아님 — 경험보고로 보완).

## 6b. ⭐ Eval-2 (F6) — 검색 미니평가 ✅ 실행 완료
> 구현=`eval2_retrieval.py`(실 검색기 import), 질의=`eval2_queries.tsv`(49개, 로컬), 결과=`RESULTS.md`/`eval2_results.csv`/`fig6_retrieval.png`(F6).
- **셋업**: 실 코퍼스 65 아티클(`archive-server.py` 그대로 import) + NL 질의 49개(골드 id, 5카테고리, 코드 일부 음차로 어휘검색에 *불리*하게).
- **비교**: ours(배포 패시지-어휘) vs BM25(word) vs BM25(char-2gram) vs dense(MiniLM-multi, 패시지청킹). 지표 R@1/R@3/MRR@10/지연/구축비용.
- **결과**: **BM25(char-2gram) R@1 81.6%** ≥ BM25(word) 75.5% ≫ **ours 42.9%** ≫ **dense 12.2%**.
- **발견①(테제 지지)**: 소규모·전문(한국어 SAP) 코퍼스에선 **어휘검색이 범용 dense를 6~7배 압도**(패시지청킹해도 유지). 솔로 운영자에겐 무인프라 어휘검색이 *타협이 아니라 더 나은 선택*. (경쟁력 있는 dense엔 도메인 파인튜닝 필요=범위 밖.)
- **발견②(실 개선 도출)**: **배포 검색기가 BM25보다 못함**(IDF·길이정규화 부재) → `search_relevant`를 BM25(char-2gram)로 교체 권고(동의어확장·패시지추출 유지). *archive-server.py=추적 도구 → 블루프린트 동기화 필요, 지금은 flag만.*
- **정직 한계**: 65문서·단일 annotator·질의당 골드 1개(소표본 CI 큼 → 자릿수 아닌 *크기*로 해석), dense 1종·무파인튜닝.

## 7. 경험보고 지표 (보조)
- 6주 단일 운영자 배포에서: 아티클 수 추이, 인테이크가 잡은 중복·충돌·정의불일치 건수, "질문→정답 위치 도달" 체감(가능하면 시간), 인수인계 검증 세션 수(공유 로그 기반). *정량 약하면 정성 서술 + 1~2개 수치.*

## 8. 그림/표 목록
- **F1** 시스템 개요(아카이브 HTML + 도구 + 대시보드 레이어, 데이터 흐름).
- **F2** 이중문서 + 불변식 + 강제동기화 루프(에이전트 변경이 전파되는 경로).
- **F3** ⭐ 충돌없는 append-only id-merge 로그(타임라인: 2세션 동시 append → 병합 → 최종상태).
- **F4** 실패모드 분류(드리프트/불일치/충돌/절단) ↔ 완화 메커니즘 매핑.
- **F5** Eval-1 결과: 충돌·lost update vs 세션 수(baseline vs ours).
- **F6** 검색 적중률/지연/구축비용 비교(패시지-어휘 vs BM25 vs dense).
- **T1** 스케일 임계점 표(N≤200/500/1000 → 방식).

## 9. 예상 리뷰어 반론 & 대응
- *"신규성 약함"* → 경험보고 + **응용 조정 프리미티브** + agentic 유지보수 규율로 프레이밍, 공백 명시.
- *"N=1"* → 인정. **통제 드리프트 실험**이 재현가능·일반화 결과 제공; 배포는 정성 보완.
- *"그냥 Notion/Obsidian+RAG 쓰면?"* → 무인프라·오프라인·무API + **에이전트 유지보수성 규율** + 단일파일 이식성 + **다중 세션 충돌없음**.

## 10. 작업 순서(제안)
1. ✅ **Eval-1 스크립트(동시 세션 + 지표 집계) → F5 완료.** 3-조건(A/B/C), 핵심 발견(원자적 append 필수), 실헬퍼 수정까지. `RESULTS.md` 참조.
2. ✅ **검색 미니평가(F6) 완료.** 49질의×65문서, BM25≫ours≫dense. 발견②=배포검색기 BM25로 교체 권고(flag). `RESULTS.md` 참조.
3. ⬜ 본문 2~4p 작성(이 아웃라인 순서) + 그림(F1~F4는 도식, **F5·F6 완료**).  ← **다음 권장**
4. ⬜ arXiv + Zenodo DOI(AINavManifest 워크플로 재사용). 자매작과 상호 인용.
   → **게재 완료 시 커리어 아카이브에 새 업적 엔트리 추가**(사용자 지시: "포스팅까지 하면 커리어 관리에도 추가").
</content>
