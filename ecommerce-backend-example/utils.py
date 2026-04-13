import logging
import inspect
import functools
import threading
import time
from typing import Any, Callable
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse


def rate_limiter(max_calls: int, period: float, by_ip: bool = True):
    """
    Rate limiter decorator.
    Args:
        max_calls: Maximum allowed calls per period.
        period: Time window in seconds.
        by_ip: If True, rate limit per client IP. If False, global.
    """
    lock = threading.Lock()
    calls = {}

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract Request object
            request = None
            for arg in list(args) + list(kwargs.values()):
                if isinstance(arg, Request):
                    request = arg
                    break
            key = request.client.host if by_ip and request else "global"
            now = time.time()
            with lock:
                timestamps = calls.get(key, [])
                # Remove timestamps outside the window
                timestamps = [t for t in timestamps if now - t < period]
                if len(timestamps) >= max_calls:
                    raise HTTPException(
                        status_code=429,
                        detail=f"Rate limit exceeded: {max_calls} per {period} seconds"
                    )
                timestamps.append(now)
                calls[key] = timestamps
            return await func(*args, **kwargs)
        return wrapper
    return decorator

def fastapi_exception_handler(log_errors: bool = True) -> Callable:
    """
    Decorator for FastAPI routes to log errors and HTTP request info.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            # Try to extract the Request object from args or kwargs
            request = None
            for arg in list(args) + list(kwargs.values()):
                if isinstance(arg, Request):
                    request = arg
                    break
            try:
                return await func(*args, **kwargs) if inspect.iscoroutinefunction(func) else func(*args, **kwargs)
            except Exception as exc:
                if log_errors:
                    if request:
                        logging.error(
                            "Error in %s %s: %s",
                            request.method,
                            request.url.path,
                            exc
                        )
                    else:
                        logging.error("Error in '%s': %s", func.__name__, exc)
                return JSONResponse(
                    status_code=500,
                    content={"detail": f"Internal server error: {exc}"}
                )
        return wrapper
    return decorator

def get_attrs_formatted(obj_ref) -> dict:
    """
    Helper function to format attributes of a Pydantic model for string representation.
    Escapes single quotes in string values to ensure valid output.

    Args:
        obj_ref: The Pydantic model instance to format.
    """
    attrs = {}
    for attr, value in vars(obj_ref).items():
        if isinstance(value, str):
            attrs[attr] = value.replace("'", "\\'")
        else:
            attrs[attr] = value
    return f"{{ {', '.join(f'{k}: {repr(v)}' for k, v in attrs.items())} }}"