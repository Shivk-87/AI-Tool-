# Pending Work and Next Steps

This file lists outstanding work items, recommended priority, and suggested owners or follow-up actions.

High priority (do these next)

1) Merge CI improvements & add batch-embeddings test
   - Branch: feat/ci-smoke-improvements (created)
   - What: apply the improved workflow (verbose docker build logs, unique image tag per run) and add a pytest test for batch embeddings.
   - Owner: repo maintainer or CI contributor
   - Status: Pending PR / merge

2) Add pytest / integration tests to CI
   - What: expand tests/ with endpoint tests for backend and model server; run pytest in CI matrix
   - Owner: backend dev / QA

3) Replace emptyDir with PVC on production Helm values (if deploying large models)
   - What: enable modelServing.pvc.enabled and configure storageClass/access size; ensure PV provisioning and CSI drivers are available
   - Owner: infra / platform

Medium priority

4) Add image publish job (optional)
   - What: CI job to build and push model-serving image to GHCR or another registry (requires secrets: REGISTRY_USERNAME, REGISTRY_TOKEN)
   - Owner: repo maintainer

5) Improve initContainer to support cloud stores securely
   - What: replace curl initImage with awscli/gsutil image or a custom model-puller that authenticates via K8s secrets or Vault
   - Owner: infra / platform

Lower priority / Nice-to-have

6) Implement /ready endpoint in model server
   - Purpose: readiness probe should return 200 only after model files are present and runtime warmup completes
   - Owner: model-serving dev

7) Observability & monitoring
   - Add Prometheus metrics, ServiceMonitor, logs collection, and tracing for model server and backend

8) Security & hardening follow-ups
   - Image signing (cosign), non-root container user, RBAC, and secret encryption at rest

How to mark items done
- Create a small PR that updates this PENDING.md (move items to COMPLETED.md with links to PR/commit) and include the PR number/commit SHA.
- Optionally use GitHub Projects or issues to track owners and assignees.

If you want, I can:
- Open a PR for the CI improvements (I prepared the changes and can push them from my fork), or
- Push tests and workflow changes directly if you grant write access.
