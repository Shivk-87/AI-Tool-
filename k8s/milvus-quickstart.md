# Milvus quickstart instructions (Helm recommended)

Milvus is recommended for production vector search. For dev or small pilots, FAISS or local numpy may suffice.

Install Milvus via Helm (community chart):

helm repo add milvus https://milvus-io.github.io/milvus-helm/
helm repo update
helm install milvus-standalone milvus/milvus --set persistence.enabled=false

After install, confirm service:

kubectl get svc -n default | grep milvus

Adjust `charts/codebase-steward/values.yaml` milvus.host/milvus.port accordingly.
