from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import TypedDict

from fastapi import FastAPI

from fury_api.lib import logging
from fury_api.lib.settings import config
from fury_api.lib.factories import ClientsFactory

__all__ = ["lifespan", "on_startup", "on_shutdown"]


class State(TypedDict):
    logger: logging.Logger


@asynccontextmanager
async def lifespan(app: FastAPI | None = None) -> AsyncGenerator[State, None]:
    await on_startup()

    state = State(
        logger=logging.get_logger(config.app.SLUG),
    )
    yield state

    await on_shutdown()


async def on_startup() -> None:
    """Executed on application startup."""
    logging.configure()


async def on_shutdown() -> None:
    """Executed on application shutdown."""
    # TODO: Leaving this here just in case it's needed later
    pass
