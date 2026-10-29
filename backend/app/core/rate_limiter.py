import time
from collections import defaultdict
from typing import Dict, List
from fastapi import Request, HTTPException, status
from app.core.config import settings

# In-memory storage: (client_ip, endpoint_tag) -> list of timestamp floats
_rate_limit_records: Dict[str, List[float]] = defaultdict(list)

def get_client_ip(request: Request) -> str:
    """Extract client IP, inspecting reverse-proxy headers if present."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "127.0.0.1"

def check_rate_limit(
    request: Request,
    endpoint_tag: str = "auth",
    limit: int = None,
    window_seconds: int = 60
) -> None:
    """
    Sliding-window IP-based rate limiter for public authentication endpoints.
    Protects against brute-force password guessing and automated registration floods.
    """
    max_requests = limit if limit is not None else settings.RATE_LIMIT_AUTH_PER_MINUTE
    client_ip = get_client_ip(request)
    key = f"{client_ip}:{endpoint_tag}"
    now = time.time()
    cutoff = now - window_seconds

    # Evict timestamps outside the sliding window
    timestamps = [ts for ts in _rate_limit_records[key] if ts > cutoff]
    
    if len(timestamps) >= max_requests:
        _rate_limit_records[key] = timestamps
        retry_after = int(window_seconds - (now - timestamps[0])) + 1
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded: Too many requests for {endpoint_tag}. Please try again in {max(1, retry_after)} seconds.",
            headers={"Retry-After": str(max(1, retry_after))}
        )

    # Record current request
    timestamps.append(now)
    _rate_limit_records[key] = timestamps

def reset_rate_limiter() -> None:
    """Reset rate limiter store (used in test fixtures for isolation)."""
    _rate_limit_records.clear()
