import os
import sys
import fnmatch
import pytest

# Make `src/` importable so we can import backend.cache
sys.path.insert(0, os.path.abspath("src"))
from backend import cache


class FakePool:
    def disconnect(self):
        # synchronous disconnect
        return None


class FakeRedis:
    def __init__(self):
        self.store = {}
        self.connection_pool = FakePool()

    async def ping(self):
        return True

    async def get(self, key):
        return self.store.get(key)

    async def setex(self, key, ttl, value):
        # store raw JSON string as the real client would
        self.store[key] = value

    async def delete(self, *keys):
        removed = 0
        for k in keys:
            if k in self.store:
                del self.store[k]
                removed += 1
        return removed

    async def close(self):
        return None

    def scan_iter(self, match=None):
        async def _gen():
            pattern = match or "*"
            for k in list(self.store.keys()):
                if fnmatch.fnmatch(k, pattern):
                    yield k
        return _gen()


@pytest.mark.asyncio
async def test_cache_lifecycle(monkeypatch):
    """Integration-like test that exercises init -> set -> get -> delete -> clear -> close."""
    fake = FakeRedis()

    # Patch redis.from_url used in the cache module to return our fake client
    monkeypatch.setattr(cache.redis, "from_url", lambda url, decode_responses=True: fake)

    # Ensure no client at start
    assert cache.redis_client is None

    # Initialize (will call fake.ping())
    await cache.init_redis()
    assert cache.redis_client is fake

    # set/get (note: cache.set_cache JSON-encodes values)
    await cache.set_cache("test:key", {"a": 1})
    val = await cache.get_cache("test:key")
    assert val == {"a": 1}

    # delete
    await cache.delete_cache("test:key")
    assert await cache.get_cache("test:key") is None

    # pattern clear
    await cache.set_cache("prefix:one", "1")
    await cache.set_cache("prefix:two", "2")
    await cache.clear_cache_pattern("prefix:*")
    assert await cache.get_cache("prefix:one") is None
    assert await cache.get_cache("prefix:two") is None

    # close
    await cache.close_redis()
    assert cache.redis_client is None
