from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List

app = FastAPI(title="Codebase Steward - Backend (scaffold)")

class IndexRequest(BaseModel):
    repo_url: str
    project: Optional[str] = None

class RetrieveResult(BaseModel):
    id: str
    snippet: str
    score: float

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/index")
async def index(req: IndexRequest):
    # Minimal stub: in real implementation this would enqueue indexing work
    return {"status": "queued", "repo_url": req.repo_url, "project": req.project}

@app.get("/retrieve", response_model=List[RetrieveResult])
async def retrieve(q: str, k: int = 3):
    # Minimal stub: return dummy results for smoke testing
    dummy = [
        {"id": f"doc-{i}", "snippet": f"Result for {q} #{i}", "score": 1.0 / (i + 1)}
        for i in range(k)
    ]
    return dummy
