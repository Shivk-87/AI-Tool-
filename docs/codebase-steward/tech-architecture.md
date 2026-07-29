# Technical Architecture — AI Codebase Steward

Core components
- Repo Fetcher: clones or connects via Git APIs, respects access controls and scans commit history.
- Text Extractor & Preprocessor: tokenizes code and extracts structured context (functions, classes, docblocks).
- Embedding Pipeline: candidate engine (OpenAI embeddings or open-source encoders) producing vectors for retrieval.
- Vector DB: FAISS / Milvus for similarity search.
- RAG Orchestrator: retrieves relevant contexts and composes prompts to LLM.
- LLM Inference: private model (Llama2, Mistral) hosted in VPC/on-prem; fallback to secure hosted inference if permitted.
- Suggestion Engine: maps LLM output to code patches, runs static checks and unit tests when available.
- CI Connector: GitHub Actions integration to surface suggestions as PR comments or suggested changes.
- UI: React dashboard for Q&A, suggestion review, audit logs, admin settings.

Tech stack recommendations
- Backend: Python (FastAPI) for APIs and pipelines.
- Frontend: React + TypeScript + Tailwind for dashboard; optional CLI in Go or Python.
- Vector DB: Milvus (managed or self-host) for enterprise use; FAISS for dev setups.
- Models: Llama2-family or private fine-tuned model; use Open-source embeddings (e.g., sentence-transformers) or managed embeddings if allowed.
- Orchestration: Kubernetes for scale; Docker for local dev.
- Secrets & Security: HashiCorp Vault for secrets, SSO (OIDC) for authentication, RBAC for actions.

Evaluation & Testing
- Unit tests for parser/extractor and indexing.
- Benchmarks for retrieval quality (MRR, Recall@k).
- Acceptance tests for suggested patches using sample PRs and CI runs.

Privacy & Compliance
- Default to local-first or VPC-deployable architecture.
- Provide data retention policies and options to purge indexed data.

