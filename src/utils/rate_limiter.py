import asyncio
from functools import wraps

def limit_async_func_call(max_size: int, waiting_time: float = 0.001):
    """
    Decorator to limit maximum concurrent async function calls.
    Uses asyncio.sleep instead of Semaphore to avoid nest-asyncio issues.
    """
    def decorator(func):
        __current_size = 0

        @wraps(func)
        async def wrapper(*args, **kwargs):
            nonlocal __current_size
            while __current_size >= max_size:
                await asyncio.sleep(waiting_time)
            __current_size += 1
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                __current_size -= 1

        return wrapper
    return decorator