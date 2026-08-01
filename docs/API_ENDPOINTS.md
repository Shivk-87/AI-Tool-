# Enhanced API Endpoints - Complete Implementation

This document describes the complete enhanced API endpoints for Codebase Steward backend.

## Overview

The API provides three main capabilities:
1. **Repository Indexing** - Async repository cloning and code analysis
2. **Vector Search** - Semantic code search using embeddings
3. **Code Suggestions** - AI-generated code improvements

## Core Features

### 1. Background Task Processing
- Non-blocking indexing with `/index` endpoint
- Progress tracking via `/index-status/{job_id}`
- Automatic database updates

### 2. Vector Search with Caching
- Query embedding generation
- Milvus vector similarity search
- 1-hour Redis caching
- Optional repository filtering

### 3. Code Improvement Suggestions
- Multiple issue types: security, lint, performance, style, refactor
- Model server integration for LLM suggestions
- 24-hour result caching
- Confidence scoring

### 4. Repository Management
- List all indexed repositories
- Get detailed repository statistics
- Track indexing status and progress

## API Endpoints

### Health Check
```
GET /health
```
Returns status of all system components (DB, Milvus, Redis).

**Response:**
```json
{
  "status": "ok",
  "version": "0.1.0",
  "db_connected": true,
  "milvus_connected": true,
  "redis_connected": true
}
```

### Index Repository
```
POST /index
```
Queue a repository for indexing (asynchronous).

**Request:**
```json
{
  "repo_url": "https://github.com/user/repo.git",
  "project": "optional-project-name"
}
```

**Response:**
```json
{
  "repo_id": "uuid-string",
  "job_id": "uuid-string",
  "status": "queued",
  "message": "Indexing job queued for repo"
}
```

### Get Indexing Status
```
GET /index-status/{job_id}
```
Get progress of an indexing job.

**Response:**
```json
{
  "job_id": "uuid-string",
  "repo_id": "uuid-string",
  "status": "running",
  "files_processed": 45,
  "total_files": 120,
  "snippets_created": 450,
  "error": null
}
```

### Search Code Snippets
```
GET /retrieve?q=search_query&k=5&repo_id=optional-repo-id
```
Search for similar code snippets using vector similarity.

**Query Parameters:**
- `q` (required): Search query (natural language or code)
- `k` (optional): Number of results, max 100, default 5
- `repo_id` (optional): Filter to specific repository

**Response:**
```json
{
  "query": "database connection",
  "results": [
    {
      "id": "snippet-id",
      "file_path": "src/db/connection.py",
      "language": "Python",
      "content": "def connect():\n  ...",
      "start_line": 10,
      "end_line": 25,
      "function_name": "connect",
      "class_name": null,
      "score": 0.95
    }
  ],
  "count": 1,
  "cached": false
}
```

### Generate Code Suggestion
```
POST /suggest
```
Generate a fix for a code issue.

**Request:**
```json
{
  "snippet_id": "snippet-uuid",
  "issue_type": "security",
  "issue_description": "SQL injection vulnerability in query"
}
```

**Response:**
```json
{
  "suggestion_id": "uuid-string",
  "snippet_id": "snippet-uuid",
  "issue_type": "security",
  "suggested_fix": "def query(sql):\n  cursor.execute(sql, params)  # Use parameterized queries",
  "confidence": 0.85
}
```

Valid `issue_type` values:
- `security` - Security vulnerabilities
- `lint` - Code style and linting issues
- `performance` - Performance optimizations
- `style` - Code formatting and style
- `refactor` - Refactoring suggestions

### List Repositories
```
GET /repositories?skip=0&limit=20
```
List all indexed repositories.

**Query Parameters:**
- `skip` (optional): Number of results to skip, default 0
- `limit` (optional): Number of results to return, default 20

**Response:**
```json
{
  "repositories": [
    {
      "id": "repo-uuid",
      "name": "my-repo",
      "url": "https://github.com/user/my-repo.git",
      "project": "team-a",
      "status": "completed",
      "last_indexed": "2026-08-01T10:30:00",
      "created_at": "2026-08-01T09:00:00"
    }
  ],
  "total": 42
}
```

### Get Repository Details
```
GET /repositories/{repo_id}
```
Get detailed information about a repository.

**Response:**
```json
{
  "id": "repo-uuid",
  "name": "my-repo",
  "url": "https://github.com/user/my-repo.git",
  "project": "team-a",
  "status": "completed",
  "last_indexed": "2026-08-01T10:30:00",
  "created_at": "2026-08-01T09:00:00",
  "snippet_count": 1250
}
```

## Architecture

### Request Flow

1. **Indexing Pipeline**
   - User calls `/index` with repo URL
   - Request validated and queued as background task
   - Repository record created in PostgreSQL
   - Background worker clones repo and parses code
   - Code chunks extracted using AST parser
   - Embeddings generated via model server
   - Results stored in PostgreSQL + Milvus
   - Status tracked in IndexJob table

2. **Search Flow**
   - User queries `/retrieve` with search text
   - Cache checked (Redis key: `retrieve:{repo_id}:{query}`)
   - If cached, return immediately with `cached: true`
   - Generate query embedding via model server
   - Search Milvus for top-k similar vectors
   - Enrich results with snippet content from PostgreSQL
   - Cache results for 1 hour
   - Return ranked results

3. **Suggestion Flow**
   - User calls `/suggest` with snippet and issue type
   - Cache checked (Redis key: `suggestion:{snippet_id}:{issue_type}`)
   - Retrieve snippet content from PostgreSQL
   - Call model server `/generate` endpoint with context
   - Store suggestion in SuggestionRequest table
   - Cache result for 24 hours
   - Return suggested fix

## Database Schema

### PostgreSQL Tables

**repositories**
- id (UUID, PK)
- name, url, project
- status (pending, running, completed, failed)
- last_indexed, created_at, updated_at

**code_snippets**
- id (UUID, PK)
- repo_id (FK)
- file_path, language, content
- start_line, end_line
- function_name, class_name, doc_string
- embedding_id (reference to Milvus)
- created_at, updated_at

**index_jobs**
- id (UUID, PK)
- repo_id (FK)
- status, celery_task_id
- total_files, processed_files, total_snippets
- error_message
- started_at, completed_at, created_at

**suggestion_requests**
- id (UUID, PK)
- snippet_id (FK)
- issue_type, issue_description
- suggested_fix, model_confidence
- created_at

### Milvus Vector Collection

**code_snippets** (1024-dim embeddings)
- id (primary key)
- repo_id
- file_path, language
- function_name, class_name
- start_line, end_line
- embedding (FLOAT_VECTOR[1024])

## Performance Optimizations

1. **Connection Pooling**
   - PostgreSQL: 20 persistent connections, 40 max overflow
   - Milvus: Single collection with IVF_FLAT indexing
   - Redis: Connection reuse via aioredis

2. **Caching Strategy**
   - Search results: 1-hour TTL
   - Suggestions: 24-hour TTL
   - Cache keys include query + repo_id for specificity

3. **Async Processing**
   - Background tasks for indexing via BackgroundTasks
   - Async HTTP calls to model server
   - Non-blocking database operations

4. **Query Limits**
   - Max k=100 results per search
   - Result pagination via skip/limit
   - Efficient Milvus filtering by repo_id

## Environment Configuration

Create `.env.local` file:

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/codebase_steward

# Milvus
MILVUS_HOST=localhost
MILVUS_PORT=19530
MILVUS_DB_NAME=codebase_steward

# Model Server
MODEL_SERVER_URL=http://localhost:8001

# Redis Cache
REDIS_URL=redis://localhost:6379/0
CACHE_TTL=3600

# Celery
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# Debug
DEBUG=false
```

## Error Handling

All endpoints return standard HTTP status codes:

- `200 OK` - Successful request
- `400 Bad Request` - Invalid parameters
- `404 Not Found` - Resource not found
- `500 Internal Server Error` - Server error with details

Error response format:
```json
{
  "detail": "Error message describing what went wrong"
}
```

## Testing

Run tests:
```bash
pytest src/backend/test_*.py -v
```

Start dev server:
```bash
uvicorn src.backend.app:app --reload --host 0.0.0.0 --port 8000
```

API documentation available at: `http://localhost:8000/docs`
