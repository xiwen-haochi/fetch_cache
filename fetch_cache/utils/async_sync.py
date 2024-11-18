import asyncio
import functools
from typing import Callable, Coroutine


def async_to_sync(f: Callable[..., Coroutine]):
    """把异步转为同步"""

    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(f(*args, **kwargs))
        else:
            loop.run_until_complete(f(*args, **kwargs))

    return wrapper


def sync_to_async(f: Callable):
    """把同步转为异步"""

    @functools.wraps(f)
    async def wrapper(*args, **kwargs):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: f(*args, **kwargs))

    return wrapper
