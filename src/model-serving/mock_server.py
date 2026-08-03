"""Mock model server for local development."""
import numpy as np
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI(title="Codebase Steward - Mock Model Server")


class EmbeddingRequest(BaseModel):
    text: Optional[str] = None
    texts: Optional[List[str]] = None


class GenerateRequest(BaseModel):
    prompt: str
    max_tokens: int = 500


@app.post("/embeddings")
async def generate_embeddings(request: EmbeddingRequest):
    """
    Generate mock embeddings (1024-dimensional).
    In production, this would use actual model like Llama2, LLaMA, or similar.
    """
    if request.text:
        # Single text embedding
        embedding = np.random.randn(1024).tolist()
        return {"embedding": embedding}
    elif request.texts:
        # Batch embeddings
        embeddings = [np.random.randn(1024).tolist() for _ in request.texts]
        return {"embeddings": embeddings}
    return {"error": "No text provided"}


@app.post("/generate")
async def generate_suggestion(request: GenerateRequest):
    """
    Generate code improvement suggestion.
    In production, this would call Llama2-13B via vLLM or TensorRT-LLM.
    """
    prompt = request.prompt
    
    # Mock response based on issue type
    if "security" in prompt.lower():
        suggestion = """# Fixed code with security improvement
def secure_query(sql, params):
    cursor.execute(sql, params)  # Use parameterized queries
    return cursor.fetchall()"""
    elif "performance" in prompt.lower():
        suggestion = """# Optimized code
def efficient_fetch(query):
    results = cache.get(query)  # Check cache first
    if not results:
        results = db.execute(query)
        cache.set(query, results, ttl=3600)
    return results"""
    else:
        suggestion = """# Improved code
def refactored_function():
    # More readable and maintainable implementation
    return process_data()"""
    
    return {
        "generated_text": suggestion,
        "tokens_used": len(suggestion.split()),
        "model": "mock-llama2-13b"
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "model": "mock-llama2-13b",
        "embedding_dim": 1024
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
