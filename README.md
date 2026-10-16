# ThirdBrain-Paper — Research on AI-Maintained Knowledge Artifacts and Failure Logs

> Research artifacts, evaluation code, benchmarks, and failure taxonomies from the Third-Party-Brain and AI-collaborative operational systems.

---

## 📚 Overview

This repository houses empirical studies and datasets examining human-AI collaborative workflows in enterprise operational settings:

### 1. Paper 1: AI-Maintained Knowledge Artifacts (Third-Party-Brain Architecture)
- **Topic**: Investigating concurrency, local retrieval latency, and synchronization integrity in single-file / file-based AI-indexable archives.
- **Documents**:
  - [`OUTLINE.md`](OUTLINE.md) — Paper design, hypotheses, evaluation protocols.
  - [`RESULTS.md`](RESULTS.md) — Experimental findings on concurrency loss, retrieval accuracy, and token economy.
- **Benchmarks & Figures**:
  - `eval1_concurrency.py`, `eval1_results.csv`, `fig5_lost_updates.png` — Multi-session write contention benchmarks.
  - `eval2_retrieval.py`, `eval2_queries.tsv`, `eval2_results.csv`, `fig6_retrieval.png` — BM25 vs dense retrieval comparison on enterprise operational queries.

### 2. Paper 2: Failure Taxonomies and Gate Evolution (`paper2_failure-log/`)
- **Title (Working)**: *Rules Decay, Tools Endure: A 4-Month Field Study on Failure Logs and Gate Evolution in Solo Operator–LLM Collaborative Enterprise ERP Operations*
- **Research Questions**:
  - **RQ1**: What fails during operational handoffs and code modification? (188 real failure incidents categorized into 11 failure types).
  - **RQ2**: Do failure patterns recur across frontier LLM generations (across 22 model era transitions)?
  - **RQ3**: Rules vs. Automated Gates: Pre/post intervention recurrence rates.
  - **RQ4**: Failure discovery agents: Operator audit vs. automated test suites vs. self-correction.
- **Artifacts**:
  - Fully anonymized incident dataset (`paper2_failure-log/data/mistakes_anon.jsonl`)
  - Codebook (`paper2_failure-log/data/codebook.md`)
  - Dual-coder inter-rater agreement evaluations (κ = 0.66 ~ 0.85).

---

## 🔒 Anonymization & Data Integrity

All operational identifiers, real personal names, client entities, and proprietary network addresses have been rigorously anonymized following the project's zero-PII security invariants. Private decoding maps (`data_private/`) are excluded from this public release.

---

## 📜 License

MIT License / CC-BY-4.0.
