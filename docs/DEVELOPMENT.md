# Development Setup Guide

## Prerequisites

- Python 3.10+
- Docker & Docker Compose (for local services)
- PostgreSQL 14+
- Redis 7+
- Milvus 2.3+

## Quick Start

### 1. Clone and Setup

```bash
git clone https://github.com/Shivk-87/AI-Tool-.git
cd AI-Tool-

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
cd src/backend
pip install -r requirements.txt
```

### 2. Configure Environment

Create `.env.local` in `src/backend/`:

```bash
# PostgreSQL
DATABASE_URL=postgresql://steward:steward@localhost:5432/codebase_steward

# Milvus
MILVUS_HOST=localhost
MILVUS_PORT=19530

# Redis
REDIS_URL=redis://localhost:6379/0

# Model Server (runs on port 8001)
MODEL_SERVER_URL=http://localhost:8001

# Debug mode
DEBUG=true
```

### 3. Start Local Services

Use Docker Compose to start PostgreSQL, Redis, and Milvus:

```bash
# From repository root
docker-compose -f docker-compose.local.yml up -d

# Check services
docker-compose -f docker-compose.local.yml ps
```

**Note:** `docker-compose.local.yml` should be created with:

```yaml
version: '3.9'

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: steward
      POSTGRES_PASSWORD: steward
      POSTGRES_DB: codebase_steward
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  milvus:
    image: milvusdb/milvus:latest
    environment:
      COMMON_STORAGETYPE: local
    ports:
      - "19530:19530"
      - "9091:9091"
    volumes:
      - milvus_data:/var/lib/milvus

volumes:
  postgres_data:
  redis_data:
  milvus_data:
```

### 4. Run Backend

```bash
cd src/backend
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

API docs: http://localhost:8000/docs

### 5. Mock Model Server (Optional)

For local development without GPU, create a mock model server:

```python
# src/model-serving/mock_server.py
from fastapi import FastAPI
import random
import numpy as np

app = FastAPI()

@app.post("/embeddings")
async def generate_embeddings(request: dict):
    # Return mock 1024-dimensional embeddings
    text = request.get("text") or request.get("texts", [""])[0]
    embedding = np.random.randn(1024).tolist()
    return {"embedding": embedding}

@app.post("/generate")
async def generate_suggestion(request: dict):
    prompt = request.get("prompt", "")
    # Return mock suggestion
    return {
        "generated_text": "# Fixed code\ndef suggested_fix():\n    pass"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
```

Run: `python src/model-serving/mock_server.py`

## Development Workflow

### Running Tests

```bash
cd src/backend
pytest test_endpoints.py -v
pytest test_endpoints.py::TestRetrieve::test_retrieve_empty_results -v
```

### Database Migrations

When updating models, recreate tables:

```python
# In Python shell
from database import init_db
init_db()  # Drops and recreates all tables
```

### Code Style

```bash
# Format code
black src/backend/

# Lint
pylint src/backend/*.py

# Type checking
mypy src/backend/app.py
```

## Project Structure

```
src/backend/
├── app.py                 # Main FastAPI application
├── config.py              # Environment configuration
├── models.py              # SQLAlchemy ORM models
├── database.py            # DB and Milvus initialization
├── cache.py               # Redis caching layer
├── embedding.py           # Model server client
├── indexing.py            # Code parsing and indexing
├── test_endpoints.py      # API endpoint tests
└── requirements.txt       # Python dependencies
```

## Troubleshooting

### Connection Errors

```bash
# Check PostgreSQL
psql -U steward -d codebase_steward -h localhost

# Check Redis
redis-cli ping

# Check Milvus
python -c "from pymilvus import connections; connections.connect(host='localhost', port=19530)"
```

### Port Conflicts

If ports are in use, update `.env.local` or docker-compose:

```bash
# Find process using port 5432
lsof -i :5432
kill -9 <PID>
```

### Memory Issues

Milvus requires significant memory. For testing, reduce `nlist` in `database.py`:

```python
# Change from 128 to 8
"params": {"nlist": 8}
```

## Next Steps

1. Implement model serving container (src/model-serving/Dockerfile)
2. Add Celery tasks for background indexing
3. Implement authentication and RBAC
4. Add comprehensive logging and monitoring
5. Deploy to Kubernetes (see docs/helm-onprem/README.md)
