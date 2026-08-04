"""Redis caching layer."""
import json
import logging
from typing import Any, Optional
import redis.asyncio as redis
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

redis_client: Optional[redis.Redis] = None


async def init_redis():
    """Initialize Redis connection."""
    global redis_client
    try:
        # decode_responses=True ensures strings are returned instead of bytes
        redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        logger.info("Connected to Redis")
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        raise


async def close_redis():
    """Close Redis connection."""
    global redis_client
    if redis_client:
        try:
            await redis_client.close()
            try:
                await redis_client.connection_pool.disconnect()
            except Exception:
                pass
        finally:
            redis_client = None
        logger.info("Closed Redis connection")


async def get_cache(key: str) -> Optional[Any]:
    """
    Retrieve value from cache.
    
    Args:
        key: Cache key
    
    Returns:
        Cached value or None if not found
    """
    if not redis_client:
        return None
    
    try:
        value = await redis_client.get(key)
        if value:
            return json.loads(value)
    except Exception as e:
        logger.warning(f"Cache get error for key {key}: {e}")
    
    return None


async def set_cache(key: str, value: Any, ttl: int = None):
    """
    Store value in cache.
    
    Args:
        key: Cache key
        value: Value to cache
        ttl: Time to live in seconds (uses default if not provided)
    """
    if not redis_client:
        return
    
    try:
        ttl = ttl or settings.CACHE_TTL
        await redis_client.setex(
            key,
            ttl,
            json.dumps(value, default=str)
        )
    except Exception as e:
        logger.warning(f"Cache set error for key {key}: {e}")


async def delete_cache(key: str):
    """Delete value from cache."""
    if not redis_client:
        return
    
    try:
        await redis_client.delete(key)
    except Exception as e:
        logger.warning(f"Cache delete error for key {key}: {e}")


async def clear_cache_pattern(pattern: str):
    """Delete all keys matching a pattern safely using SCAN."""
    if not redis_client:
        return
    
    try:
        keys = [key async for key in redis_client.scan_iter(match=pattern)]
        if keys:
            await redis_client.delete(*keys)
            logger.info(f"Cleared {len(keys)} cache entries for pattern {pattern}")
    except Exception as e:
        logger.warning(f"Cache pattern delete error: {e}")


def cache_key_for_retrieve(query: str, repo_id: Optional[str] = None) -> str:
    """Generate cache key for retrieve endpoint."""
    if repo_id:
        return f"retrieve:{repo_id}:{query}"
    return f"retrieve:all:{query}"


def cache_key_for_suggestion(snippet_id: str, issue_type: str) -> str:
    """Generate cache key for suggestion endpoint."""
    return f"suggestion:{snippet_id}:{issue_type}"
