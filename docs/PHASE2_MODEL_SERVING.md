# Phase 2: Model Serving - Implementation Guide

## Overview

Model Serving is the backbone of the AI-assisted code review system. This phase implements:

1. **vLLM-based inference server** for Llama2-13B
2. **Request batching** for optimal GPU utilization
3. **Token streaming** for real-time responses
4. **Embedding generation** for vector search
5. **Production-ready containerization**

---

## Architecture

```
┌─────────────────┐
│  FastAPI Backend │
│  (Port 8000)    │
└────────┬────────┘
         │
    HTTP Request
         │
         ▼
┌──────────────────────────────────────────┐
│  Model Serving Server (Port 8001)        │
│  ┌────────────────────────────────────┐  │
│  │  Request Router                    │  │
│  │  - /embeddings                     │  │
│  │  - /generate (completions)         │  │
│  │  - /batch_infer                    │  │
│  │  - /health                         │  │
│  └────────────────────────────────────┘  │
│          │              │                 │
│          ▼              ▼                 │
│  ┌───────────────┐  ┌──────────────────┐ │
│  │ vLLM Server   │  │ Embedding Model  │ │
│  │ (Llama2-13B)  │  │ (BGE or similar) │ │
│  └───────┬───────┘  └────────┬─────────┘ │
│          │                   │            │
│          └─────────┬─────────┘            │
│                    ▼                      │
│         ┌────────────────────┐            │
│         │  GPU Memory (VRAM) │            │
│         │  - Model weights   │            │
│         │  - KV Cache        │            │
│         │  - Batch tensors   │            │
│         └────────────────────┘            │
└──────────────────────────────────────────┘
         │
    HTTP Response
         │
         ▼
┌─────────────────┐
│  FastAPI Backend │
│  (Processes)    │
└─────────────────┘
```

---

## Prerequisites

### Hardware
- **GPU**: NVIDIA A100 (40GB) or H100 (80GB) recommended
- **CPU**: 8-16 cores for preprocessing/batching
- **RAM**: 64-128GB system memory
- **VRAM**: 40GB+ for Llama2-13B quantized

### Software
- NVIDIA CUDA 12.1+
- Python 3.10+
- Docker & NVIDIA Container Toolkit

### Installation Check

```bash
# Check CUDA
nvcc --version

# Check GPU
nvidia-smi

# Expected: Tesla A100 or H100 with 40GB+ VRAM
```

---

## Components

### 1. Production Model Server (`inference_server.py`)

**Features:**
- vLLM backend for fast inference
- Embedding model integration
- Request batching (configurable batch size)
- Token streaming for long outputs
- Quantization support (INT8/INT4)
- Health monitoring
- Structured logging

**Endpoints:**
- `POST /embeddings` - Generate code embeddings
- `POST /generate` - Generate text completions
- `POST /batch_infer` - Batch inference
- `GET /health` - Health check
- `GET /models` - Loaded models info

### 2. Docker Container (`Dockerfile`)

**Base Image:**
- `nvidia/cuda:12.2-devel-ubuntu22.04`

**Contents:**
- vLLM 0.2.0+
- Llama2-13B model (quantized)
- Embedding model (BGE-large)
- Python dependencies
- Optimization libraries (flash-attn, etc.)

### 3. Kubernetes Deployment (`deployment.yaml`)

**Configuration:**
- GPU resource requests
- Memory limits
- Health probes
- Service exposure
- PersistentVolume for models

---

## Implementation Steps

### Step 1: Create Production Model Server

```python
# src/model-serving/inference_server.py
```

**Key Classes:**
- `ModelConfig` - Model settings
- `EmbeddingModel` - Embedding inference
- `GenerationModel` - Text generation
- `BatchProcessor` - Batch management
- `RequestRouter` - Endpoint handling

### Step 2: Create Dockerfile

```dockerfile
# src/model-serving/Dockerfile
```

**Stages:**
1. Base: CUDA with Python
2. Build: Install dependencies
3. Runtime: Copy models and optimize

### Step 3: Environment Setup

```bash
# src/model-serving/.env.production
```

**Configuration:**
- Model paths
- Batch size
- Quantization method
- GPU memory fraction

### Step 4: Kubernetes Manifests

```yaml
# k8s/model-serving-deployment.yaml
```

**Resources:**
- 1x GPU (A100 40GB)
- 16 CPU cores
- 64GB RAM
- 100GB storage for models

---

## Performance Optimization

### 1. Quantization

```python
# INT8 Quantization
model_kwargs = {
    "load_in_8bit": True,
    "device_map": "auto"
}

# Saves ~50% VRAM, 10% speed overhead
```

### 2. Batching

```python
# Configure batch size
batch_size = 32
max_batch_wait_ms = 100  # Max wait time

# Throughput: 32 requests * (tokens/req) per batch
```

### 3. KV-Cache Optimization

```python
# Enable paged attention (vLLM)
kwargs = {
    "use_v2": True,
    "max_num_seqs": 256,
    "max_model_len": 2048
}
```

### 4. Token Streaming

```python
# Stream tokens as generated
# Reduces perceived latency
# Better UX for code suggestions
```

---

## Configuration

### Model Selection

| Model | VRAM | Speed | Quality | Best For |
|-------|------|-------|---------|----------|
| Llama2-7B | 16GB | 200 tok/s | Good | Testing |
| Llama2-13B | 40GB | 100 tok/s | Excellent | Production |
| Llama2-70B | 160GB | 50 tok/s | Best | Large-scale |
| CodeLlama-13B | 40GB | 100 tok/s | Code ✅ | Code tasks |

### Batch Configuration

```python
# Recommended settings
if gpu_memory == "40GB":    # A100
    batch_size = 16
elif gpu_memory == "80GB":  # H100
    batch_size = 32
```

### Quantization Impact

```
No Quantization: 40GB VRAM, 100 tok/s
INT8:            20GB VRAM, 95 tok/s   (-50% memory, -5% speed)
INT4:            12GB VRAM, 90 tok/s   (-70% memory, -10% speed)
```

---

## Deployment Options

### Option 1: Docker Standalone

```bash
# Build image
docker build -t codebase-steward/model-serving:latest \
  -f src/model-serving/Dockerfile \
  src/model-serving/

# Run container
docker run --gpus all -p 8001:8001 \
  -v /models:/models \
  codebase-steward/model-serving:latest
```

### Option 2: Kubernetes

```bash
# Apply deployment
kubectl apply -f k8s/model-serving-deployment.yaml

# Check pod
kubectl get pods -l app=model-serving
kubectl logs -f -l app=model-serving
```

### Option 3: Docker Compose (Dev)

```yaml
model-serving:
  build:
    context: src/model-serving
    dockerfile: Dockerfile.dev
  ports:
    - "8001:8001"
  environment:
    - MODEL_ID=meta-llama/Llama-2-13b-hf
    - BATCH_SIZE=16
  volumes:
    - ~/.cache/huggingface:/root/.cache/huggingface
```

---

## API Usage

### Generate Embeddings

```bash
curl -X POST http://localhost:8001/embeddings \
  -H "Content-Type: application/json" \
  -d '{"text": "def hello(): return world"}'

# Response
{
  "embedding": [0.123, -0.456, ...],  # 1024 dimensions
  "model": "bge-large-en-v1.5",
  "tokens_used": 10
}
```

### Generate Code Suggestion

```bash
curl -X POST http://localhost:8001/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Fix the SQL injection vulnerability...",
    "max_tokens": 500,
    "temperature": 0.7,
    "top_p": 0.9
  }'

# Response (streaming)
{
  "generated_text": "def secure_query():\n    cursor.execute(sql, params)\n...",
  "tokens_used": 250,
  "model": "llama-2-13b"
}
```

### Batch Inference

```bash
curl -X POST http://localhost:8001/batch_infer \
  -H "Content-Type: application/json" \
  -d '{
    "texts": [
      "def func1(): pass",
      "def func2(): pass",
      "def func3(): pass"
    ],
    "task": "embeddings"
  }'

# Response
{
  "results": [
    {"embedding": [...], "id": 0},
    {"embedding": [...], "id": 1},
    {"embedding": [...], "id": 2}
  ],
  "batch_size": 3,
  "processing_time_ms": 45
}
```

---

## Monitoring & Logging

### Metrics

```python
# Track via Prometheus
request_latency_ms = histogram('request_latency')
batch_size_histogram = histogram('batch_size')
gpu_memory_usage = gauge('gpu_memory_mb')
model_throughput = counter('tokens_generated')
```

### Health Checks

```bash
# Liveness probe (is server alive?)
curl http://localhost:8001/health

# Readiness probe (can accept requests?)
curl http://localhost:8001/ready

# Expected response
{
  "status": "healthy",
  "gpu_available": true,
  "models_loaded": ["llama-2-13b", "bge-large"],
  "current_load": 0.35,
  "queue_length": 5
}
```

### Logs

```
[2026-08-01 10:30:15] INFO: Starting model server
[2026-08-01 10:30:20] INFO: Loading model llama-2-13b...
[2026-08-01 10:30:45] INFO: Model loaded. VRAM: 38.5GB / 40GB
[2026-08-01 10:31:00] INFO: Embeddings model loaded
[2026-08-01 10:31:05] INFO: Server ready. Listening on 0.0.0.0:8001
[2026-08-01 10:31:10] INFO: Request /generate | batch=1 | tokens=250 | time=1250ms
```

---

## Scaling

### Single-GPU Setup

```
Throughput: ~100 tokens/sec
Latency: ~50ms per request
Max batch: 16-32 requests
```

### Multi-GPU Setup (Tensor Parallelism)

```python
# Distribute model across 2-4 GPUs
model_parallel_size = 2  # Requires 80GB+ total

# Throughput: 180-200 tokens/sec
# Each GPU handles partial layers
```

### Model Sharding (LoRA Fine-tuning)

```python
# For multiple models
# Model 1: Security checks (8GB)
# Model 2: Performance (8GB)
# Model 3: Style (8GB)
# Total: 24GB per GPU
```

---

## Troubleshooting

### Out of Memory

```bash
# Error: CUDA out of memory

# Solutions:
# 1. Reduce batch size
batch_size = 8  # Instead of 16

# 2. Enable quantization
load_in_8bit = True

# 3. Use smaller model
# Llama2-7B instead of 13B

# 4. Reduce max_model_len
max_model_len = 1024  # Instead of 2048
```

### Slow Inference

```bash
# Check GPU utilization
nvidia-smi dmon

# Should see >80% GPU usage

# If low:
# 1. Increase batch size
# 2. Reduce max_model_len
# 3. Check network latency (TCP_NODELAY)
# 4. Enable flash-attention
```

### Model Load Failure

```bash
# Error: Failed to load model

# Solutions:
# 1. Check HuggingFace credentials
export HF_TOKEN=your_token

# 2. Pre-download model
python -c "from transformers import AutoModel; AutoModel.from_pretrained('meta-llama/Llama-2-13b-hf')"

# 3. Use local model path
MODEL_PATH=/models/llama-2-13b
```

---

## Production Checklist

- [ ] Model selected and tested (Llama2-13B or CodeLlama)
- [ ] Quantization method chosen (INT8 recommended)
- [ ] Batch size configured (16-32 recommended)
- [ ] Dockerfile built and tested
- [ ] Health checks configured
- [ ] Monitoring/logging setup
- [ ] Kubernetes manifests created
- [ ] GPU resources allocated
- [ ] Storage for models provisioned
- [ ] Load testing completed (100+ req/sec)
- [ ] Security hardened (TLS, auth)
- [ ] Documentation updated

---

## Next: Integration with Backend

Once model serving is running:

1. Update backend `config.py` with model server URL
2. Test `/embeddings` and `/generate` endpoints
3. Integrate embedding pipeline in indexing
4. Test code suggestion feature
5. Monitor latency and throughput

---

## References

- **vLLM**: https://github.com/lm-sys/vLLM
- **Llama2**: https://huggingface.co/meta-llama/Llama-2-13b-hf
- **BGE Embeddings**: https://huggingface.co/BAAI/bge-large-en-v1.5
- **NVIDIA Container Toolkit**: https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/
