import asyncio
from functools import wraps
from typing import Callable


class _RateLimitCounter:
    """Per-function rate limit counter to avoid shared state issues."""
    _counters: dict[int, int] = {}
    
    @classmethod
    def get(cls, func_id: int) -> int:
        return cls._counters.get(func_id, 0)
    
    @classmethod
    def increment(cls, func_id: int) -> None:
        cls._counters[func_id] = cls._counters.get(func_id, 0) + 1
    
    @classmethod
    def decrement(cls, func_id: int) -> None:
        cls._counters[func_id] = cls._counters.get(func_id, 0) - 1


def limit_async_func_call(max_size: int, waiting_time: float = 0.001) -> Callable:
    """
    Decorator to limit maximum concurrent async function calls.
    Uses asyncio.sleep instead of Semaphore to avoid nest-asyncio issues.
    Each decorated function has its own independent counter.
    """
    def decorator(func: Callable) -> Callable:
        func_id = id(func)
        
        @wraps(func)
        async def wrapper(*args, **kwargs):
            while _RateLimitCounter.get(func_id) >= max_size:
                await asyncio.sleep(waiting_time)
            _RateLimitCounter.increment(func_id)
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                _RateLimitCounter.decrement(func_id)
        
        return wrapper
    return decorator