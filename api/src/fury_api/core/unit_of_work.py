from __future__ import annotations

from contextlib import asynccontextmanager, suppress
from typing import TypeVar

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel

from fury_api.lib.db import AsyncSqlAlchemyUnitOfWork
from fury_api.lib.repository import GenericSqlExtendedRepository
from fury_api.lib.settings import config

__all__ = ["UnitOfWork", "UnitOfWorkError", "UnitOfWorkRepositoryNotFoundError"]

T = TypeVar("T", bound=SQLModel)


class UnitOfWork(AsyncSqlAlchemyUnitOfWork):
    def __init__(
        self,
        session_factory: sessionmaker,
        autocommit: bool = False,
        autocommit_ignore_nested: bool = True,
        *,
        organization_id: int | None = None,
        read_only: bool = False,
        query_user: bool = False,
    ):
        super().__init__(session_factory, autocommit, autocommit_ignore_nested)
        self.organization_id = organization_id
        self.read_only = read_only
        self.query_user = query_user

    async def __aenter__(self) -> UnitOfWork:
        """This method is called when entering the context manager."""
        if self.is_in_context:
            return await super().__aenter__()

        # Avoid circular import
        from fury_api.domain.organizations.repository import OrganizationRepository
        from fury_api.domain.users.repository import UserRepository
        from fury_api.domain.earthquakes.repository import EarthquakeRepository

        self.organizations = OrganizationRepository()
        self.users = UserRepository()
        self.earthquakes = EarthquakeRepository()

        self._repos = {
            repo._model_cls: repo
            for repo in (
                self.organizations,
                self.users,
                self.earthquakes,
            )
        }

        return await super().__aenter__()

    async def __aexit__(self, *args: tuple, **kwargs: dict) -> None:
        """This method is called when exiting the context manager."""
        await super().__aexit__(*args, **kwargs)

        if self.is_in_context:
            return

        del self._repos
        del self.organizations
        del self.users
        del self.earthquakes

    def get_repository(self, model_cls: type[T]) -> GenericSqlExtendedRepository[T]:
        """Return the repository for the given model class."""
        repo = self._repos.get(model_cls)
        if repo is None:
            raise UnitOfWorkRepositoryNotFoundError(model_cls)
        return repo

    @asynccontextmanager
    async def with_organization(
        self, organization_id: int, *, read_only: bool | None = None, query_user: bool | None = None
    ) -> UnitOfWork:
        """Context manager to change the current organization."""
        if self.organization_id is not None and organization_id != self.organization_id:
            raise ValueError("Cannot change organization_id when already in a tenant context")

        backup_args = (self.organization_id, self.read_only, self.query_user)

        async with self:
            self.organization_id = organization_id
            if read_only is not None:
                self.read_only = read_only
            if query_user is not None:
                self.query_user = query_user

            await self.post_begin_session_hook()
            try:
                yield self
                await self.pre_commit_hook()
            finally:
                self.organization_id, self.read_only, self.query_user = backup_args

    async def post_begin_session_hook(self) -> None:
        """This method is called after creating a new session."""
        if config.database.TENANT_ROLE_ENABLED and self.organization_id is not None:
            if self.query_user:
                await self.session.exec(text(f"set session role {config.database.TENANT_QUERY_ROLE_RO}"))
            elif self.read_only:
                await self.session.exec(text(f"set session role {config.database.TENANT_ROLE_RO}"))
            else:
                await self.session.exec(text(f"set session role {config.database.TENANT_ROLE}"))
            await self.session.exec(text(f"set {config.database.TENANT_PARAMETER} = {self.organization_id}"))

    async def pre_commit_hook(self) -> None:
        """This method is called before committing the session."""
        if self._context_depth > 1:
            return

        with suppress(SQLAlchemyError):
            await self.session.exec(text("reset role"))


class UnitOfWorkError(Exception):
    """Base exception for UnitOfWork errors."""


class UnitOfWorkRepositoryNotFoundError(UnitOfWorkError):
    """Raised when a repository is not found."""

    def __init__(self, model_cls: type[SQLModel]):
        super().__init__(f"No repository found for model {model_cls.__name__}")
        self.model_cls = model_cls
