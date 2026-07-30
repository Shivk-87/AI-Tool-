# On-Prem Helm/Cluster Guide for Codebase Steward

This guide helps you deploy the Codebase Steward app and model-serving infrastructure on an on-prem Kubernetes cluster.

Prerequisites
- Kubernetes cluster with GPU nodes (NVIDIA GPUs). Drivers + NVIDIA device plugin installed.
- Helm 3 installed on your control machine.
- At least 1 GPU node with 80+ GB RAM for Llama2-13B (recommended: A100 40GB or H100 80GB). For inference-serving you may need model parallelism or optimized runtimes.
- Storage (NFS/Ceph) or PVs for Milvus and model artifacts.

Recommended resource sizing for Llama2-13B (inference)
- Single-fast inference (low concurrency): H100/A100 80GB or 2x A100 40GB with model sharding.
- Memory: 64–128 GB RAM on the node.
- CPU: 8–16 cores for handling preprocessing and batching.

Deployment steps
1. Install Milvus (optional for vector DB):
   helm repo add milvus https://milvus-io.github.io/milvus-helm/
   helm repo update
   helm install milvus-standalone milvus/milvus --set persistence.enabled=false

2. Install Postgres (for metadata):
   kubectl apply -f k8s/postgres-deployment.yaml

3. Deploy model-serving (requires GPU node):
   kubectl apply -f k8s/model-serving-deployment.yaml
   Note: replace image and ensure PV for /models is available, or mount external model store.

4. Deploy the app with Helm:
   helm upgrade --install codebase-steward charts/codebase-steward -f charts/codebase-steward/values.yaml

Secrets & credentials
- Store private repo PATs, model-store credentials, and other secrets in HashiCorp Vault or Kubernetes secrets. Do not commit them.
- Use an init-container to pull models from a secure model store if desired.

Scaling & production notes
- For multi-tenant, run dedicated model-serving replicas per tenant or use model server that supports multiple models.
- Use horizontal autoscaling for the backend, but model-serving requires careful GPU scaling.
- Monitor GPU utilization and memory to tune batch sizes and concurrency.

Safety & governance
- Add RBAC to restrict who can trigger indexing against private repos.
- Add audit logs for all indexing and suggestion actions.

