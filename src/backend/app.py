"""FastAPI application for Codebase Steward backend."""
import logging
import uuid
from typing import Optional, List
from datetime import datetime

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from config import get_settings
from database import get_db, init_db, milvus_store
from cache import init_redis, close_redis, get_cache, set_cache, cache_key_for_retrieve, cache_key_for_suggestion
from models import Repository, CodeSnippet, IndexJob, SuggestionRequest, IndexStatusEnum
from indexing import RepositoryIndexer
from embedding import embedding_client

logger = logging.getLogger(__name__)
settings = get_settings()

# Initialize FastAPI app
app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    description="AI-Assisted Enterprise Codebase Steward API"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Request/Response Models
# ============================================================================

class IndexRequest(BaseModel):
    """Request to index a repository."""
    repo_url: str
    project: Optional[str] = None


class IndexResponse(BaseModel):
    """Response for index request."""
    repo_id: str
    job_id: str
    status: str
    message: str


class RetrieveResult(BaseModel):
    """A single code search result."""
    id: str
    file_path: str
    language: str
    content: str
    start_line: int
    end_line: int
    function_name: Optional[str] = None
    class_name: Optional[str] = None
    score: float


class RetrieveResponse(BaseModel):
    """Response for retrieve/search request."""
    query: str
    results: List[RetrieveResult]
    count: int
    cached: bool = False


class SuggestionRequestModel(BaseModel):
    """Request for code improvement suggestion."""
    snippet_id: str
    issue_type: str  # security, lint, performance, etc.
    issue_description: str


class SuggestionResponse(BaseModel):
    """Response for suggestion request."""
    suggestion_id: str
    snippet_id: str
    issue_type: str
    suggested_fix: str
    confidence: float


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    db_connected: bool
    milvus_connected: bool
    redis_connected: bool


class IndexStatusResponse(BaseModel):
    """Status of an indexing job."""
    job_id: str
    repo_id: str
    status: str
    files_processed: int
    total_files: int
    snippets_created: int
    error: Optional[str] = None


# ============================================================================
# Startup/Shutdown
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize connections on startup."""
    logger.info("Starting Codebase Steward backend...")
    
    try:
        # Initialize databases
        init_db()
        
        # Initialize Redis
        await init_redis()
        
        logger.info("Backend initialized successfully")
    except Exception as e:
        logger.error(f"Startup error: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on shutdown."""
    logger.info("Shutting down Codebase Steward backend...")
    
    try:
        await close_redis()
    except Exception as e:
        logger.error(f"Shutdown error: {e}")


# ============================================================================
# Health Check
# ============================================================================

@app.get("/health", response_model=HealthResponse)
async def health(db: Session = Depends(get_db)):
    """
    Health check endpoint.
    
    Returns status of all system components.
    """
    db_connected = False
    milvus_connected = False
    redis_connected = False
    
    # Check database
    try:
        db.execute("SELECT 1")
        db_connected = True
    except Exception as e:
        logger.warning(f"Database health check failed: {e}")
    
    # Check Milvus
    try:
        if milvus_store.collection:
            milvus_connected = True
    except Exception as e:
        logger.warning(f"Milvus health check failed: {e}")
    
    # Check Redis
    try:
        from cache import redis_client
        if redis_client:
            await redis_client.ping()
            redis_connected = True
    except Exception as e:
        logger.warning(f"Redis health check failed: {e}")
    
    return HealthResponse(
        status="ok" if all([db_connected, milvus_connected, redis_connected]) else "degraded",
        version=settings.API_VERSION,
        db_connected=db_connected,
        milvus_connected=milvus_connected,
        redis_connected=redis_connected
    )


# ============================================================================
# Indexing Endpoints
# ============================================================================

async def index_repository_background(repo_url: str, project: str, db_session: Session):
    """Background task for repository indexing."""
    try:
        indexer = RepositoryIndexer(db_session)
        result = indexer.index_repository(repo_url, project)
        logger.info(f"Background indexing completed: {result}")
    except Exception as e:
        logger.error(f"Background indexing failed: {e}")


@app.post("/index", response_model=IndexResponse)
async def index(
    req: IndexRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Queue a repository for indexing.
    
    This endpoint starts an asynchronous indexing job. The actual indexing
    runs in the background. Use `/index-status/{job_id}` to check progress.
    
    Args:
        req: Index request with repo_url and optional project name
    
    Returns:
        Job details with repo_id and job_id
    """
    try:
        # Validate repo URL
        if not req.repo_url.endswith(".git") and not req.repo_url.startswith("https://"):
            raise HTTPException(status_code=400, detail="Invalid repository URL")
        
        # Add background task
        background_tasks.add_task(index_repository_background, req.repo_url, req.project, db)
        
        # Create placeholder repository record
        repo_id = str(uuid.uuid4())
        repo_name = req.repo_url.split("/")[-1].replace(".git", "")
        
        repo = Repository(
            id=repo_id,
            name=repo_name,
            url=req.repo_url,
            project=req.project,
            status=IndexStatusEnum.PENDING
        )
        db.add(repo)
        db.commit()
        
        job_id = str(uuid.uuid4())
        
        return IndexResponse(
            repo_id=repo_id,
            job_id=job_id,
            status="queued",
            message=f"Indexing job queued for {repo_name}"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Index error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/index-status/{job_id}", response_model=IndexStatusResponse)
async def index_status(job_id: str, db: Session = Depends(get_db)):
    """
    Get status of an indexing job.
    
    Args:
        job_id: The job ID returned from /index endpoint
    
    Returns:
        Current status of the indexing job
    """
    try:
        job = db.query(IndexJob).filter(IndexJob.id == job_id).first()
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        return IndexStatusResponse(
            job_id=job.id,
            repo_id=job.repo_id,
            status=job.status.value,
            files_processed=job.processed_files,
            total_files=job.total_files,
            snippets_created=job.total_snippets,
            error=job.error_message
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Index status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Search/Retrieve Endpoints
# ============================================================================

@app.get("/retrieve", response_model=RetrieveResponse)
async def retrieve(
    q: str,
    k: int = 5,
    repo_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Search for similar code snippets by query.
    
    Uses vector similarity search to find relevant code.
    Results are cached for 1 hour.
    
    Args:
        q: Search query (free text or code)
        k: Number of results (max 100, default 5)
        repo_id: Optional filter by specific repository
    
    Returns:
        List of code snippets ranked by similarity
    """
    try:
        # Validate k parameter
        k = min(max(1, k), settings.VECTOR_SEARCH_LIMIT)
        
        # Check cache
        cache_key = cache_key_for_retrieve(q, repo_id)
        cached_result = await get_cache(cache_key)
        
        if cached_result:
            cached_result["cached"] = True
            return cached_result
        
        # Generate embedding for query
        query_embedding = await embedding_client.generate_embedding(q)
        
        # Search Milvus
        hits = milvus_store.search_similar(query_embedding, top_k=k, repo_id=repo_id)
        
        # Enrich results with snippet content from PostgreSQL
        results = []
        for hit in hits:
            snippet = db.query(CodeSnippet).filter(CodeSnippet.id == hit["id"]).first()
            
            if snippet:
                results.append(RetrieveResult(
                    id=snippet.id,
                    file_path=snippet.file_path,
                    language=snippet.language,
                    content=snippet.content,
                    start_line=snippet.start_line,
                    end_line=snippet.end_line,
                    function_name=snippet.function_name,
                    class_name=snippet.class_name,
                    score=1.0 / (1.0 + hit["distance"])  # Convert distance to similarity
                ))
        
        response = RetrieveResponse(
            query=q,
            results=results,
            count=len(results),
            cached=False
        )
        
        # Cache result
        await set_cache(cache_key, response.model_dump())
        
        return response
    
    except Exception as e:
        logger.error(f"Retrieve error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Suggestion Endpoints
# ============================================================================

@app.post("/suggest", response_model=SuggestionResponse)
async def suggest(
    req: SuggestionRequestModel,
    db: Session = Depends(get_db)
):
    """
    Generate code improvement suggestion.
    
    Analyzes a code snippet and generates a fix for the specified issue type.
    Results are cached for 24 hours.
    
    Args:
        req: Suggestion request with snippet_id, issue_type, and issue_description
    
    Returns:
        Suggested fix with confidence score
    """
    try:
        # Validate issue type
        valid_types = {"security", "lint", "performance", "style", "refactor"}
        if req.issue_type.lower() not in valid_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid issue_type. Must be one of: {', '.join(valid_types)}"
            )
        
        # Check cache
        cache_key = cache_key_for_suggestion(req.snippet_id, req.issue_type)
        cached_result = await get_cache(cache_key)
        
        if cached_result:
            return SuggestionResponse(**cached_result)
        
        # Get code snippet
        snippet = db.query(CodeSnippet).filter(CodeSnippet.id == req.snippet_id).first()
        
        if not snippet:
            raise HTTPException(status_code=404, detail="Snippet not found")
        
        # Generate suggestion via model server
        suggested_fix = await embedding_client.suggest_fix(
            snippet.content,
            req.issue_type,
            req.issue_description
        )
        
        # Create suggestion record
        suggestion_id = str(uuid.uuid4())
        suggestion = SuggestionRequest(
            id=suggestion_id,
            snippet_id=req.snippet_id,
            issue_type=req.issue_type,
            issue_description=req.issue_description,
            suggested_fix=suggested_fix,
            model_confidence=0.8  # Placeholder confidence
        )
        db.add(suggestion)
        db.commit()
        
        response = SuggestionResponse(
            suggestion_id=suggestion_id,
            snippet_id=req.snippet_id,
            issue_type=req.issue_type,
            suggested_fix=suggested_fix,
            confidence=0.8
        )
        
        # Cache result (24 hours)
        await set_cache(cache_key, response.model_dump(), ttl=86400)
        
        return response
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Suggestion error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Repository Management Endpoints
# ============================================================================

@app.get("/repositories")
async def list_repositories(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """
    List indexed repositories.
    
    Args:
        skip: Number of results to skip
        limit: Number of results to return
    
    Returns:
        List of repositories with metadata
    """
    try:
        repos = db.query(Repository).offset(skip).limit(limit).all()
        
        return {
            "repositories": [
                {
                    "id": r.id,
                    "name": r.name,
                    "url": r.url,
                    "project": r.project,
                    "status": r.status.value,
                    "last_indexed": r.last_indexed,
                    "created_at": r.created_at,
                }
                for r in repos
            ],
            "total": db.query(Repository).count()
        }
    
    except Exception as e:
        logger.error(f"List repositories error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/repositories/{repo_id}")
async def get_repository(repo_id: str, db: Session = Depends(get_db)):
    """
    Get details of a specific repository.
    
    Args:
        repo_id: Repository ID
    
    Returns:
        Repository details with snippet count
    """
    try:
        repo = db.query(Repository).filter(Repository.id == repo_id).first()
        
        if not repo:
            raise HTTPException(status_code=404, detail="Repository not found")
        
        snippet_count = db.query(CodeSnippet).filter(CodeSnippet.repo_id == repo_id).count()
        
        return {
            "id": repo.id,
            "name": repo.name,
            "url": repo.url,
            "project": repo.project,
            "status": repo.status.value,
            "last_indexed": repo.last_indexed,
            "created_at": repo.created_at,
            "snippet_count": snippet_count
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get repository error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
