# Completed Work (Phase 2 + infra changes)

This file documents what has already been implemented and merged to main (or otherwise added to the repo).

High-level items

- Model serving artifacts
  - src/model-serving/Dockerfile — Docker image to run the mock FastAPI server (uvicorn)
  - src/model-serving/requirements.txt — runtime Python dependencies
  - (Mock server present in docs for local testing: src/model-serving/mock_server.py as described in docs/DEVELOPMENT.md)

- Kubernetes & Helm
  - k8s/model-serving-deployment-updated.yaml — example Deployment with initContainer scaffold, probes, and emptyDir volume
  - charts/codebase-steward/values.yaml — extended with modelServing section
  - charts/codebase-steward/templates/model-serving-deployment.yaml — templated Deployment for model-serving
  - charts/codebase-steward/templates/model-serving-service.yaml — Service for model-serving
  - charts/codebase-steward/templates/pvc.yaml — PVC template (applies when modelServing.pvc.enabled = true)
  - charts/codebase-steward/README-model-serving.md — documentation for Helm modelServing values
  - charts/codebase-steward/values-vault.yaml — example values showing secret usage
  - k8s/example-model-store-secret.yaml — sample secret manifest used by initContainer example

- Documentation
  - docs/helm-onprem/HARDENING.md — hardening and production guidance for model serving
  - docs/PHASE2_MODEL_SERVING.md, docs/DEVELOPMENT.md and IMPLEMENTATION_SUMMARY.md — project docs and walkthroughs (see docs/)

- CI
  - .github/workflows/ci-smoke-model-serving.yml — GitHub Actions smoke-test workflow that builds the model-serving image and validates /health, /generate, /embeddings

- Helm branch and follow-ups
  - feat/ci-smoke-improvements (branch created) — branch intended for CI workflow improvements and tests (pending PR/merge)

Notes
- The Dockerfile is configured to run uvicorn on port 8001: CMD ["uvicorn", "src.model-serving.mock_server:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "1"]
- The current k8s example uses emptyDir for models for quick testing; the Helm chart supports toggling PVC via modelServing.pvc.enabled.

If you need a quick link list to any file I can add it here; tell me what format you prefer (plain list, markdown links, or table).
