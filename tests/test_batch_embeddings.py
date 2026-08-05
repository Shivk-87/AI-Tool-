import os
import sys
import pytest
from typing import List

# Make `src/` importable so we can import backend.embedding
sys.path.insert(0, os.path.abspath("src"))
from backend import embedding

class FakeHTTPXClient:
    async def post(self, url, json):
        # Simulate a batch embedding response
        texts = json.get("texts") or [json.get("text")]
        return type("R", (), {"json": lambda: {"embeddings": [[0.1]*16 for _ in texts], "embedding":[0.1]*16}, "raise_for_status": lambda: None})

@pytest.mark.asyncio
async def test_generate_batch_embeddings_monkeypatched(monkeypatch):
    fake = FakeHTTPXClient()
    # Patch httpx.AsyncClient used inside EmbeddingClient to return our fake
    monkeypatch.setattr(embedding.httpx, "AsyncClient", lambda *args, **kwargs: fake)

    client = embedding.EmbeddingClient()
    texts: List[str] = ["a", "b", "c"]
    embeddings = await client.generate_batch_embeddings(texts)
    assert isinstance(embeddings, list)
    assert len(embeddings) == len(texts)
    assert all(isinstance(e, list) for e in embeddings)
