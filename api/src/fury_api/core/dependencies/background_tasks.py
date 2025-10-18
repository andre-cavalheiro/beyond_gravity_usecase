import asyncio
from collections.abc import Awaitable, Callable
from typing import Any, TypeAlias

from fastapi import BackgroundTasks

__all__ = ["get_async_background_tasks", "AsyncBackgroundTasks"]

AsyncBackgroundTasks: TypeAlias = BackgroundTasks


def get_async_background_tasks(background_tasks: BackgroundTasks) -> AsyncBackgroundTasks:
    """Extends FastAPI's BackgroundTasks to handle both synchronous and asynchronous tasks.

    This function modifies the add_task method of the given BackgroundTasks instance
    to properly handle awaitables, coroutine functions, and regular functions.
    """
    original_add_task = background_tasks.add_task

    def add_task(func: Callable[..., Any] | Awaitable, *args: Any, **kwargs: Any) -> None:
        if isinstance(func, Awaitable):
            original_add_task(asyncio.get_running_loop().create_task, func)
        elif asyncio.iscoroutinefunction(func):
            original_add_task(asyncio.get_running_loop().create_task, func(*args, **kwargs))
        elif callable(func):
            original_add_task(func, *args, **kwargs)
        else:
            raise TypeError("Task must be an awaitable, a coroutine function, or a callable")

    background_tasks.add_task = add_task
    return background_tasks
