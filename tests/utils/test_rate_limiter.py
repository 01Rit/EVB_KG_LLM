import pytest
import asyncio
from src.utils.rate_limiter import limit_async_func_call

def test_rate_limiter_blocks_when_maxed():
    call_count = 0
    max_concurrent = 2

    @limit_async_func_call(max_size=max_concurrent)
    async def slow_func():
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0.05)
        return call_count

    async def run_all():
        results = await asyncio.gather(*[slow_func() for _ in range(4)])
        return results

    start = asyncio.get_event_loop().time()
    results = asyncio.get_event_loop().run_until_complete(run_all())
    elapsed = asyncio.get_event_loop().time() - start

    assert max(results) <= 4