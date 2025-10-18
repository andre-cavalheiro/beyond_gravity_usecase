from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from sqlmodel.ext.asyncio.session import AsyncSession

from fury_api.lib.serializers import json_deserializer, json_serializer
from fury_api.lib.settings import config
from fury_api.lib.unit_of_work import AsyncAbstractUnitOfWork

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


class AsyncSqlAlchemyUnitOfWork(AsyncAbstractUnitOfWork):
    def __init__(
        self, session_factory: sessionmaker, autocommit: bool = False, autocommit_ignore_nested: bool = True
    ) -> None:
        self._session_factory = session_factory
        self.session: AsyncSession | None = None

        self.autocommit = autocommit
        self.autocommit_ignore_nested = autocommit_ignore_nested
        self._context_depth = 0

        super().__init__()

    @property
    def is_in_context(self) -> bool:
        return self._context_depth > 0

    @property
    def is_root_context(self) -> bool:
        return self._context_depth == 1

    async def _begin_new_session(self) -> AsyncSession:
        self.session = self._session_factory()
        await self.post_begin_session_hook()
        return self.session

    async def __aenter__(self) -> AsyncSqlAlchemyUnitOfWork:
        """This method is called when entering the context manager."""
        self._context_depth += 1

        if self.session is None:
            await self._begin_new_session()

        return await super().__aenter__()

    async def __aexit__(self, *args: tuple, **kwargs: dict) -> None:
        """This method is called when exiting the context manager."""
        self._context_depth -= 1

        if self.is_in_context:
            if args and args[0] is not None:
                return
            if self.autocommit and not self.autocommit_ignore_nested:
                await self.commit()
            return

        try:
            if args and args[0] is not None:
                await self.rollback()
            else:
                if self.autocommit:
                    await self.commit()

            await super().__aexit__(*args, **kwargs)
            await self.session.close()
        finally:
            self.session = None

    async def commit(self) -> None:
        if self.session is not None:
            await self.pre_commit_hook()
            await self.session.commit()

    async def rollback(self) -> None:
        if self.session is not None:
            await self.session.rollback()

    async def post_begin_session_hook(self) -> None:
        """This method is called after creating a new session."""
        pass

    async def pre_commit_hook(self) -> None:
        """This method is called before committing the session."""
        pass
