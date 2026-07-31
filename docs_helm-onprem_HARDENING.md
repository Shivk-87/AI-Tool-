# Hardening notes & next steps

This run describes the work done in branch feat/helm-onprem-vault-hardening and next steps to finalize production readiness.

Completed
- Helm templates updated to include Vault init container scaffold (deployment.yaml)
- PVC templates added for model storage and Milvus
- PodDisruptionBudget added
- Model-serving deployment updated to reference a real inference runtime (TGI) and mount a PVC
- GitHub Actions workflow added: runs unit tests and an optional smoke test on feature branches
- Prometheus ServiceMonitor & Grafana dashboard scaffolding added

Next steps (recommended)
1. Replace the vault init container with Vault Agent Injector or Vault CSI (production secure injection).
2. Provide actual storageClass names and ensure PVs are available in your cluster.
3. Configure Milvus Helm chart and persistence; test index & query flows.
4. Add liveness/startup probes for the model server and tune resources based on profiling.
5. Integrate Fluentd/EFK or Loki for log aggregation and connect Grafana dashboards to metrics.

How to apply (example)
- kubectl apply -f k8s/vault-init-example.yaml -n codebase-steward
- Update charts/codebase-steward/values.yaml (or use values-vault.yaml) with your cluster settings
- helm upgrade --install codebase-steward charts/codebase-steward -n codebase-steward -f charts/codebase-steward/values-vault.yaml