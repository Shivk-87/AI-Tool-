"""Embedding generation and vector operations."""
import logging
import httpx
from typing import List
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class EmbeddingClient:
    """Client for generating embeddings via model server."""
    
    def __init__(self):
        self.base_url = settings.MODEL_SERVER_URL
        self.embedding_endpoint = settings.MODEL_EMBEDDING_ENDPOINT
        self.timeout = 30.0
    
    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Input text to embed
        
        Returns:
            Embedding vector
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}{self.embedding_endpoint}",
                    json={"text": text}
                )
                response.raise_for_status()
                data = response.json()
                return data.get("embedding", [])
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise
    
    async def generate_batch_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts: List of input texts
        
        Returns:
            List of embedding vectors
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}{self.embedding_endpoint}",
                    json={"texts": texts}
                )
                response.raise_for_status()
                data = response.json()
                return data.get("embeddings", [])
        except Exception as e:
            logger.error(f"Failed to generate batch embeddings: {e}")
            raise
    
    async def suggest_fix(self, code: str, issue_type: str, issue_description: str) -> str:
        """
        Generate code suggestion using model server.
        
        Args:
            code: Code snippet
            issue_type: Type of issue (security, lint, performance, etc.)
            issue_description: Description of the issue
        
        Returns:
            Suggested fix
        """
        try:
            prompt = f"""You are a code review expert. Fix the following {issue_type} issue:

Issue: {issue_description}

Code:
```
{code}
```

Provide ONLY the fixed code without explanations."""
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}{settings.MODEL_SUGGEST_ENDPOINT}",
                    json={"prompt": prompt, "max_tokens": 500}
                )
                response.raise_for_status()
                data = response.json()
                return data.get("generated_text", "")
        except Exception as e:
            logger.error(f"Failed to generate suggestion: {e}")
            raise


embedding_client = EmbeddingClient()
