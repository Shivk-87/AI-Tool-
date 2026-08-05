import os
import sys
import pytest
from typing import List

# Make `src/` importable so we can import backend.embedding
sys.path.insert(0, os.path.abspath("src"))
from backend import embedding


class FakeResponse:
    def __init__(self, embeddings=None, embedding=None):
        self._data = {}
        if embeddings is not None:
            self._data["embeddings"] = embeddings
        if embedding is not None:
            self._data["embedding"] = embedding

    def json(self):
        return self._data

    def raise_for_status(self):
        return None


class FakeAsyncClient:
    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, json):
        texts = json.get("texts") or ([json.get("text")] if json.get("text") else [])
        # return deterministic small embeddings (dim 16)
        emb = [[0.1] * 16 for _ in texts]
        single = [0.1] * 16
        if texts:
            return FakeResponse(embeddings=emb, embedding=single)
        return FakeResponse(embeddings=[], embedding=single)


@pytest.mark.asyncio
async def test_generate_batch_embeddings_monkeypatched(monkeypatch):
    """Mock the httpx.AsyncClient used by EmbeddingClient to validate batch behavior."""
    # Patch httpx.AsyncClient inside the embedding module
    monkeypatch.setattr(embedding, "httpx", type("m", (), {"AsyncClient": FakeAsyncClient}))

    client = embedding.EmbeddingClient()
    texts: List[str] = ["first", "second", "third"]
    embeddings = await client.generate_batch_embeddings(texts)

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
