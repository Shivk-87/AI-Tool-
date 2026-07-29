# MVP Sprint Plan — AI Codebase Steward

Duration: 10 weeks (recommended)
Team: 2 backend engineers, 1 frontend engineer, 1 security/infra engineer, 1 product/QA (part-time), 1 DSP not needed here.

Sprint 0 (Week 0) — Discovery & Setup
- Collect 3 representative private repositories (with permission) and identify sensitive data policy.
- Choose vector DB (FAISS/Milvus), model infra (private LLM or secure RAG), and CI integration strategy (GitHub Actions initially).
- Provision dev infra (VPC, sandbox repos, testing CI org).

Sprint 1 (Weeks 1–2) — Indexing & Retrieval
- Implement repo fetcher that clones and streams file content into indexer.
- Build text extractor for code, comments, README, and commit messages.
- Implement vectorization pipeline and store embeddings in chosen vector DB.
- Deliverable: indexed sample repo; API to query top-k results.

Sprint 2 (Weeks 3–4) — RAG Q&A + Grounding
- Wire a lightweight RAG pipeline: retriever -> prompt template -> LLM inference (private or secure hosted)
- Implement answer grounding: show sources (file paths, line ranges) with snippets and confidence.
- Deliverable: dev UI to ask questions against indexed repo and return grounded answers.

Sprint 3 (Weeks 5–6) — Code Action Suggestions
- Implement targeted suggestion engine for one rule class (e.g., fix common security lint: SQL injection, unsafe deserialization).
- Produce patch suggestions as diff/PR-ready content with tests where applicable.
- Deliverable: CLI or UI flow that creates a suggested patch and a preview of changes.

Sprint 4 (Weeks 7–8) — CI Integration & Safety
- Create a GitHub Action that runs the assistant on PRs and posts suggestions as PR comments or suggested changes (draft PRs).
- Add safety gates: human approval workflow, audit logging, rate limiting.
- Deliverable: working integration in test org with sample PRs.

Sprint 5 (Weeks 9–10) — Pilot & Hardening
- Run 2–3 week pilot with an internal or partner team, gather feedback and telemetry.
- Improve retrieval precision, reduce hallucinations, add evaluation tests for suggestion acceptance.
- Deliverable: pilot report, backlog for v1 improvements.

Optional Weeks 11–12 — On‑Prem Packaging & Docs
- Package as deployable appliance (Docker Compose/Kubernetes Helm) with secure onboarding docs and RBAC.


