--- a/dev-null +++ b/docs/TODO-ISSUES.md @@ -0,0 +1,220 @@ +# TODO: Issues to bring the repo to deployable state + +This file enumerates the missing items discovered by a brief automated checklist and provides ready-to-create GitHub issue titles and bodies. Create one issue per numbered item, assign owners, and track progress. + +--- + +1) Issue title: Add minimal backend scaffold (src/backend) so CI can run

Description:
The repository currently lacks application source code referenced by CI (.github/workflows/ci.yml expects src/backend). Add a minimal ASGI backend (FastAPI/uvicorn) with basic endpoints so unit-tests and the smoke test can run.
Suggested tasks:
Create src/backend/app.py with a /health endpoint and minimal index/retrieve stubs used by the smoke test.
Add src/backend/__init__.py as needed.
Add src/backend/requirements.txt with packages used by the scaffold (fastapi, uvicorn, pydantic).
Add a basic pytest under tests/test_health.py that asserts /health returns 200.
Acceptance criteria:
pytest runs locally and in CI against the new scaffold.
The CI smoke-test (start backend + /index + /retrieve) does not fail because of missing module imports.
Files to change/create:
src/backend/app.py
src/backend/requirements.txt
tests/test_health.py
+--- + +2) Issue title: Add Dockerfile(s) and image build/publish job to CI

Description:
There is no Dockerfile or image build pipeline. Add Dockerfile(s) for the backend and document how images are built/pushed to your registry. Add a GitHub Actions job to build and (optionally) push images on merges to main or tagged releases.
Suggested tasks:
Add Dockerfile at repo root or src/backend/Dockerfile.
Add ci/build-image.yml or extend existing CI with a build job that uses buildx and pushes to GHCR/ECR/GCR as configured by secrets.
Document required secrets in docs/helm-onprem/HARDENING.md.
Acceptance criteria:
docker build produces an image that runs the backend scaffold.
CI has a successful build job on the feature branch or PR (can be gated to main).
Files to change/create:
Dockerfile(s)
.github/workflows/build-image.yml (or extend ci.yml)
docs/helm-onprem/HARDENING.md (registry secrets docs)
+--- + +3) Issue title: Implement model artifact management (download or model-store integration)

Description:
The manifests mount /models but there is no mechanism to provision model files. Implement one of:
Init container that pulls model artifacts from a secure model store (S3/Vault-protected store), or
Use a shared PV populated by an external process, or
Integrate with a model-store image and document auth.
Suggested tasks:
Add an initContainer spec (templated in Helm) that pulls model files using credentials from Vault secrets (or document how to mount model store).
Update values-vault.yaml with a modelPull configuration (store URL, credentials secret name).
Add startup/liveness probes for the model server after models are present.
Acceptance criteria:
Model files are present at /models in model server pods after boot.
Model server reports healthy and serves requests (basic inference smoke test).
Files to change/create:
charts/codebase-steward/templates/* (model init container template)
docs/helm-onprem/HARDENING.md (model-store instructions)
+--- + +4) Issue title: Finalize StorageClass / PV strategy for model & Milvus PVCs

Description:
values-vault.yaml leaves storageClass empty (cluster defaults used). Identify production StorageClass names or add static PV definitions for clusters without dynamic provisioning.
Suggested tasks:
Determine StorageClass names for your cluster (e.g. gp2, standard, rook-ceph-block) and update values-vault.yaml.
Add example PVs or instructions in HARDENING.md for clusters with no dynamic provisioner.
Acceptance criteria:
Helm templates produce PVCs that bind in the target cluster without manual PV creation.
Documented StorageClass values in values-vault.yaml.
Files to change/create:
charts/codebase-steward/values-vault.yaml
docs/helm-onprem/HARDENING.md
+--- + +5) Issue title: Vault configuration & Kubernetes auth role guide + Agent Injector setup

Description:
The chart uses Vault Agent Injector annotations but the repo lacks step-by-step Vault configuration for k8s auth role, policies, and example Vault installation (or instructions to install the injector).
Suggested tasks:
Add detailed commands to HARDENING.md for:
Code
- enabling k8s auth in Vault,
Code
- creating a policy that exposes only required secrets,
Code
- creating the k8s auth role mapping to the service account (codebase-steward-sa).
Add instructions to install Vault Agent Injector (or Vault CSI) in the target cluster.
Acceptance criteria:
Following the doc, an operator can configure Vault and inject secrets as files into the pod.
No Vault tokens are written into commit history or printed to logs in any example.
Files to change/create:
docs/helm-onprem/HARDENING.md (expanded vault section)
+--- + +6) Issue title: Pin container images & add network policies and PodSecurity

Description:
For production hardening, pin images to digests, add NetworkPolicies to limit traffic between components, and set PodSecurity constraints (PSP or Pod Security admission labels).
Suggested tasks:
Update values-vault.yaml to include imageDigest fields or replace tags with pinned digests.
Add example NetworkPolicy resources to charts/templates or k8s/observability.
Add recommended PodSecurity labels/annotations to templates.
Acceptance criteria:
Charts reference pinned images or document a digest pinning process.
Example NetworkPolicy applied in test cluster restricts access to Milvus/Postgres/model server only to backend.
Files to change/create:
charts/codebase-steward/values-vault.yaml
charts/codebase-steward/templates/networkpolicy.yaml (new)
+--- + +7) Issue title: Add model server readiness/liveness/startup probes and resource tuning

Description:
The model-serving manifest has resource requests/limits but lacks tuned readiness/startup probes to reflect model load time. Add startup probe and tune resources based on profiling.
Suggested tasks:
Add startupProbe to model server manifest with a long initialDelay/period to tolerate model load.
Add readinessProbe that verifies the model is loaded (HTTP health + model-ready endpoint).
Add guidance for resource values in values-vault.yaml.
Acceptance criteria:
Model server starts, loads model, transitions to Ready, and exposes a /health or /ready endpoint that can be probed.
Files to change/create:
k8s/model-serving-deployment-updated.yaml or charts template
docs/helm-onprem/HARDENING.md (resource guidance)
+--- + +8) Issue title: Tests & CI: add unit tests and integrate Milvus smoke test

Description:
The new CI workflow references tests that don't exist. Add unit tests for the backend and an optional integration job that runs the Milvus pymilvus sanity check (containerized) or a mock test in CI to validate index+retrieve.
Suggested tasks:
Add pytest tests under tests/ for the backend endpoints.
Add a CI job that runs the pymilvus script in a container (or uses a Milvus test harness) only for integration branches or scheduled jobs.
Acceptance criteria:
pytest passes for the scaffolded backend.
Integration test (optional) verifies Milvus is reachable and performs a basic search.
Files to change/create:
tests/*.py
.github/workflows/ci.yml (extend the integration step)
+--- + +Notes +- Each item above is intentionally small and actionable. When you create the issues, link them from this file and assign owners. If you prefer, I can create the issues in the repository automatically — tell me and I will (I will need permission to create issues in the repo). +- I can also generate a PR that adds this file to a branch for review, or produce separate individual issue creation payloads. + +---

How to apply (commands)

Create a branch, apply the file, push, and open a PR (recommended): git checkout -b chore/add-todo-issues
