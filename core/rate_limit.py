
from slowapi import Limiter
from slowapi.util import get_remote_address

from .config import RATE_LIMIT_DEFAULT, REDIS_URL

# In-memory storage for development (when Redis not available)
_storage = {}

def get_rate_limit_key(request) -> str:
    """Extract rate limit key from request (IP or API key)."""
    # Try to get API key from header
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return f"apikey:{api_key}"
    # Fall back to IP address
    return get_remote_address(request)


# Try to configure Redis storage
redis_client = None
try:
    import redis.asyncio as redis
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    # Use Redis storage for production
    from slowapi.extension import RedisStorage
    storage = RedisStorage(redis_client)
except Exception:
    # Fall back to in-memory storage for development
    storage = None

# Create limiter with appropriate storage
if storage:
    limiter = Limiter(key_func=get_rate_limit_key, storage_uri=REDIS_URL)
else:
    limiter = Limiter(key_func=get_rate_limit_key)
    # Apply default rate limit to all endpoints
    limiter._default_limits = [RATE_LIMIT_DEFAULT]
