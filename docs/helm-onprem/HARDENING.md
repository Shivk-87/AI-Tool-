# Hardening & Resource Guidance for On-Prem Model Serving

This document supplements the Helm/k8s runbook with concrete guidance to harden and resource the model-serving component (Phase 2: Model Serving).

What's included
- A simple Kubernetes Deployment manifest (k8s/model-serving-deployment-updated.yaml) that includes:
  - An initContainer scaffold to pull model artifacts from a model store (templated to read MODEL_STORE_URL from a Kubernetes Secret named `model-store-secret`).
  - An emptyDir volume mounted at /models for quick testing. Replace with PVC for production.
  - Readiness and liveness probes hitting /health on the model server.
  - Resource requests & limits; add GPU device requests if deploying to GPU nodes.

Recommendations for production
1. Model artifacts and init containers
   - Use a robust init container that understands your model store (S3, GCS, Artifactory) and authenticates securely.
   - Prefer a CSI driver or a pre-populated PV/PVC for large models instead of copying at startup.
   - Store model URLs and credentials in a secret manager (Vault, K8s secrets encrypted by KMS) and never check them into git.

2. Probes & startup
   - Implement both startup and readiness probes if model initialization can take long. The readiness probe should fail until the model is fully loaded.
   - Consider an HTTP /ready endpoint in the model server that returns 200 only when model files are present and the runtime has finished warmup.

3. Resources & GPUs
   - Set resource requests/limits based on profiling. For GPU servers, request the appropriate device plugin resource (e.g., nvidia.com/gpu).
   - Use node selectors / taints & tolerations to ensure model server pods land on GPU nodes.

4. Security
   - Run the container as non-root if the runtime supports it. Add a dedicated service account and minimal RBAC rules.
   - Use image signing/origin verification where possible (e.g., cosign).

5. Observability
   - Export metrics (prometheus) from the model server (request latencies, model load time, OOM events).
   - Add logs collection and centralize traces/metrics.

6. CI / smoke tests
   - Add a CI job that builds the model-server image and runs a containerized smoke test against /health and a simple /generate or /embeddings call (this can be run only on scheduled or feature branches as acceptance tests).

Next steps performed in this commit
- Added src/model-serving/Dockerfile to build a model-serving image for local development (runs the existing mock_server FastAPI app).
- Added src/model-serving/requirements.txt listing runtime deps used by the Dockerfile.
- Added k8s/model-serving-deployment-updated.yaml with initContainer scaffold and readiness/liveness probes.
- Added this HARDENING.md file under docs/helm-onprem to describe production hardening steps and guidance.

How to use locally
1. Build the image:
   docker build -t ghcr.io/<your-org>/model-serving:local -f src/model-serving/Dockerfile .
2. Run locally:
   docker run --rm -p 8001:8001 ghcr.io/<your-org>/model-serving:local
3. Verify:
   curl http://localhost:8001/health

If you'd like, I can also:
- Add a Helm values template for the initContainer (values.yaml + deployment template changes).
- Add a basic smoke test to .github/workflows/ci.yml that builds the image and curls /health.
