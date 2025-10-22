from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from sqlmodel.ext.asyncio.session import AsyncSession

from fury_api.lib.serializers import json_deserializer, json_serializer
from fury_api.lib.settings import config
from fury_api.lib.unit_of_work import AsyncSqlAlchemyUnitOfWork

from . import base

__all__ = [
    "base",
    "engine",
    "engine_ro",
    "async_session",
    "async_session_ro",
    "AsyncSqlAlchemyUnitOfWork",
    "AsyncSession",
]


def _create_engine(*, read_only: bool = False) -> AsyncEngine:
    return create_async_engine(
        url=(config.database.READ_ONLY_URL if read_only else None) or config.database.URL,
        echo=config.database.ECHO,
        echo_pool=config.database.ECHO_POOL,
        max_overflow=config.database.POOL_MAX_OVERFLOW,
        pool_size=config.database.POOL_SIZE,
        pool_timeout=config.database.POOL_TIMEOUT,
        poolclass=NullPool if config.database.POOL_DISABLED else None,
        pool_pre_ping=config.database.POOL_PRE_PING,
        connect_args=config.database.CONNECT_ARGS
        | {"application_name": config.app.SLUG, "options": f"-c search_path={config.database.SCHEMA}"},
        json_serializer=json_serializer,
        json_deserializer=json_deserializer,
        execution_options={"postgresql_readonly": read_only},
    )


engine_ro: AsyncEngine = _create_engine(read_only=True)
engine: AsyncEngine = _create_engine(read_only=config.database.FORCE_READ_ONLY)

async_session_ro: sessionmaker[AsyncSession] = sessionmaker(
    bind=engine_ro, class_=AsyncSession, expire_on_commit=False, info={"read_only": True}
)
async_session: sessionmaker[AsyncSession] = sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False, info={"read_only": config.database.FORCE_READ_ONLY}
)
