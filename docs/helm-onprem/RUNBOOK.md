# Runbook: Deploy Codebase Steward On-Prem (Helm + K8s)

This runbook describes step-by-step actions to deploy the Codebase Steward stack to an on‑prem Kubernetes cluster using the Helm chart in charts/codebase-steward and the supporting manifests in k8s/. It assumes a cluster with at least one GPU node for Llama2-13B model serving.

Important: Do NOT store secrets (PATs, model store keys) in the chart values. Use HashiCorp Vault or Kubernetes secrets as indicated.

Pre-requisites
- kubectl configured to the target cluster context.
- Helm 3 installed and configured.
- NVIDIA drivers + device plugin installed on GPU nodes (if model-serving uses GPUs).
- Storage class available for PVs (or acceptable to use emptyDir for dev).
- Access to Docker registry for images referenced in the chart; if private, ensure nodes can pull images.

Cluster preparation
1. Verify nodes and GPU availability:
   - kubectl get nodes -o wide
   - kubectl describe node <gpu-node> | grep -i nvidia
2. Install NVIDIA device plugin (if needed):
   - kubectl apply -f https://raw.githubusercontent.com/NVIDIA/k8s-device-plugin/main/nvidia-device-plugin.yml
3. Set up a namespace for the deployment (recommended):
   - kubectl create namespace codebase-steward

Secrets & vault
1. If using Vault, authenticate and create Kubernetes secrets or use the Vault CSI driver.
2. Create a Kubernetes secret for Postgres (example):
   - kubectl create secret generic postgres-secret -n codebase-steward --from-literal=password=<STRONG_PASSWORD>
3. Do NOT put any secret values into Git. Use the Helm values to reference secrets.

Milvus (vector DB) — optional but recommended
1. Install via Helm (dev/test):
   - helm repo add milvus https://milvus-io.github.io/milvus-helm/
   - helm repo update
   - helm install milvus-standalone milvus/milvus --namespace codebase-steward --set persistence.enabled=false
2. Confirm Milvus is running:
   - kubectl get pods -n codebase-steward | grep milvus
3. Update charts/codebase-steward/values.yaml milvus.host/milvus.port if different.

Postgres (metadata)
1. Apply the manifest (this uses emptyDir for quick testing):
   - kubectl apply -f k8s/postgres-deployment.yaml -n codebase-steward
2. Wait until the postgres pod is Running.

Model-serving (Llama2-13B) — dev scaffold
1. Edit k8s/model-serving-deployment.yaml to point to your model-server image and model path. If using a private registry, ensure imagePullSecrets are configured.
2. Deploy model serving to the GPU node(s):
   - kubectl apply -f k8s/model-serving-deployment.yaml -n codebase-steward
3. Confirm the pod is scheduled on a GPU node and has GPU resources allocated.

Deploy the application (Helm)
1. Review charts/codebase-steward/values.yaml and set the following as needed:
   - image.repository / tag
   - milvus.enabled and host/port
   - modelServing.gpu.nodeSelector / tolerations (if needed)
2. Install/upgrade the chart:
   - helm upgrade --install codebase-steward charts/codebase-steward -n codebase-steward -f charts/codebase-steward/values.yaml
3. Check pods and services:
   - kubectl get pods -n codebase-steward
   - kubectl get svc -n codebase-steward

Smoke test the service locally
1. Port forward the service:
   - kubectl port-forward svc/codebase-steward-service 8000:8000 -n codebase-steward
2. Health:
   - curl http://localhost:8000/health
3. Index a small public repo (example):
   - curl -X POST http://localhost:8000/index -H 'Content-Type: application/json' -d '{"repo_url":"https://github.com/octocat/Hello-World.git","project":"hello-world"}'
4. Retrieve a query:
   - curl "http://localhost:8000/retrieve?q=readme&k=5"

Troubleshooting
- Pod CrashLoopBackOff: check pod logs kubectl logs <pod> -n codebase-steward
- Model server OOM: reduce batch size or provision larger GPU memory machine
- Milvus connection errors: confirm service name and port; check milvus pod logs
- Postgres connection errors: check secrets and env variables in deployment

Upgrade & rollback
- To upgrade the chart with new values:
  - helm upgrade codebase-steward charts/codebase-steward -n codebase-steward -f charts/codebase-steward/values.yaml
- To rollback:
  - helm rollback codebase-steward <revision> -n codebase-steward

Observability & logging
- Attach Prometheus/Grafana for metrics; consider node exporter for GPU metrics.
- Centralize logs via EFK/ELK or a log-forwarder.

Security & governance
- Enable RBAC for the namespace and restrict who can update the Helm release.
- Require approval for any automated PRs or patching that writes to pilot repos.

Runbook ownership & contacts
- Maintainers: <Your Name or Team>
- On-call escalation: <Ops contact>

Change log
- 2026-07-30: Initial runbook added to feat/helm-onprem branch.

