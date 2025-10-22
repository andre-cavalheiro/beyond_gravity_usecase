import asyncio
import contextlib

from collections.abc import AsyncGenerator, Awaitable, Callable
from functools import wraps
from typing import Any, Generic, TypeVar, List, cast, TYPE_CHECKING

from sqlmodel.ext.asyncio.session import AsyncSession

from fury_api.lib.unit_of_work import UnitOfWork
from fury_api.lib.db.base import BaseSQLModel
from fury_api.lib.logging import Logger, get_logger
from fury_api.lib.repository import GenericSqlExtendedRepository
from fury_api.lib.model_filters import Filter, Sort
from fury_api.lib.pagination import CursorPage

if TYPE_CHECKING:
    from fury_api.domain.users.models import UserAuth

__all__ = ["GenericService", "SqlService", "with_uow", "with_uow_class", "ServiceError"]

T = TypeVar("T", bound=BaseSQLModel)
F = TypeVar("F", bound=Callable[..., Any])


def with_uow_class(cls):
    with contextlib.suppress(WithUowRequiresAsyncError):
        for name, method in cls.__dict__.items():
            if callable(method):
                setattr(cls, name, with_uow(method))
    return cls


def with_uow(func: F) -> F:
    if not callable(func):
        raise WithUowRequiresCallableError

    if not asyncio.iscoroutinefunction(func):
        if not callable(func):
            raise WithUowRequiresAsyncError
        return func

    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        if not isinstance(self, SqlService):
            raise WithWowRequiresServiceError

        if getattr(self, "uow", None) is None:
            raise WithWowRequiresUowError

        with contextlib.suppress(Exception):
            self.logger_bind(method=func.__name__)
        try:
            async with self.uow:
                return await func(self, *args, **kwargs)
        finally:
            with contextlib.suppress(Exception):
                self.logger_bind(method=None)

    return cast(F, wrapper)


class GenericService:
    def __init__(
        self,
        logger: Logger | None = None,
        logger_bind_allows: bool | None = None,
        **kwargs: Any,
    ):
        self._allow_logger_bind = logger_bind_allows if logger_bind_allows is not None else logger is None
        self._logger = logger or get_logger(name=self.__class__.__name__)

    @contextlib.contextmanager
    def override_attributes(self, **kwargs: Any) -> None:
        backup = {}
        new_attrs = {}
        for key, value in kwargs.items():
            if hasattr(self, key):
                backup[key] = getattr(self, key)
                setattr(self, key, value)
            else:
                new_attrs[key] = value
        try:
            yield
        finally:
            for key, value in backup.items():
                setattr(self, key, value)
            for key in new_attrs:
                delattr(self, key)

    @property
    def logger(self):
        return self._logger

    def logger_bind(self, **kwargs: Any) -> Logger:
        if self._allow_logger_bind:
            self._logger = self._logger.bind(**kwargs)
        return self._logger


class SqlService(Generic[T], GenericService):
    def __init__(
        self,
        model_cls: type[T],
        uow: UnitOfWork,
        *,
        model_id_attr: str | None = None,
        auth_user: "UserAuth | None" = None,
        no_repository: bool = False,
        **kwargs: Any,
    ):
        super().__init__(**kwargs)
        self._model_cls = model_cls
        self._id_attr = model_id_attr or getattr(model_cls, "__id_attr__", "id")

        if not no_repository and (self._id_attr is None or not hasattr(self._model_cls, self._id_attr)):
            raise ServiceModelNoIdAttrError(self._model_cls)

        self.uow = uow
        self.auth_user = auth_user

        self._no_repository = no_repository

        self.logger_bind(service=self.__class__.__name__, uow=self.uow)

    @property
    def session(self) -> AsyncSession | None:
        return self.uow.session

    @property
    def repository(self) -> GenericSqlExtendedRepository[T]:
        if self._no_repository:
            raise AttributeError("Service has no repository.")  # noqa: TRY003
        return self.uow.get_repository(self._model_cls)

    @property
    def organization_id(self) -> int | None:
        if self.auth_user is not None:
            return self.auth_user.organization_id
        if self.uow is not None and self.uow.organization_id is not None:
            return self.uow.organization_id
        return None

    @property
    def user_id(self) -> int | None:
        if self.auth_user is not None:
            return self.auth_user.user_id
        return None

    @with_uow
    async def create_item(self, item: BaseSQLModel) -> BaseSQLModel:
        return await self.repository.add(self.session, item)

    @with_uow
    async def create_items(self, items: List[BaseSQLModel]) -> int:
        count = 0
        for item in items:
            try:
                await self.repository.add(self.session, item)
                count += 1
            except Exception as e:
                print(f"Failed to add item: {item}, error: {e}")
                continue
        return count

    @with_uow
    async def get_item(self, id_: int) -> BaseSQLModel | None:
        return await self.repository.get_by_id(self.session, id_)

    @with_uow
    async def get_items(
        self, *, model_filters: list[Filter] | None = None, model_sorts: list[Sort] | None = None
    ) -> AsyncGenerator[BaseSQLModel, Any]:
        for search in await self.repository.list(self.session, model_filters=model_filters, model_sorts=model_sorts):
            yield search

    @with_uow
    async def get_items_paginated(
        self, *, model_filters: list[Filter] | None = None, model_sorts: list[Sort] | None = None
    ) -> CursorPage[BaseSQLModel]:
        return await self.repository.list_with_pagination(
            self.session, model_filters=model_filters, model_sorts=model_sorts
        )

    @with_uow
    async def delete_item(
        self,
        item: BaseSQLModel,
    ) -> None:
        item = await self.repository.delete(self.session, item.id)
        return item

    @with_uow
    async def update_item(
        self,
        item_id: int,
        item: BaseSQLModel,
        *,
        commit: bool = True,
    ) -> BaseSQLModel:
        """
        Update an item using a model instance.

        :param item: The model instance with updated values (must have its ID set)
        :param commit: Whether to commit after update
        :return: The updated model from the DB
        """
        updates = item.dict(exclude_unset=True)
        return await self.repository.update_by_id(
            session=self.session,
            entity_id=item_id,
            updates=updates,
            commit=commit,
        )

    def _set_audit_fields(self, obj: T) -> T:
        if self.organization_id is not None:
            obj.organization_id = self.organization_id
        if self.user_id is not None:
            obj.updated_by_id = self.user_id
        return obj

    def _parse_to_model(self, model: T | dict[str, Any]) -> T:
        return model if isinstance(model, self._model_cls) else self._model_cls(**model)

    def _parse_to_dict(self, model: T | dict[str, Any]) -> dict[str, Any]:
        return model if isinstance(model, dict) else model.dict()


class ServiceError(Exception):
    """Base class for Service errors."""


class ServiceModelNoIdAttrError(ServiceError):
    """Raised when a model does not have an id attribute."""

    def __init__(self, model_cls: type[BaseSQLModel]):
        super().__init__(f"Model {model_cls.__name__} does not have an id attribute.")
        self.model_cls = model_cls


class WithUowRequiresCallableError(ServiceError):
    """Raised when with_uow decorator is used on a non-callable."""

    def __init__(self):
        super().__init__("with_uow decorator requires a callable.")


class WithUowRequiresAsyncError(ServiceError):
    """Raised when with_uow decorator is used on a non-async function."""

    def __init__(self):
        super().__init__("with_uow decorator requires an async function.")


class WithWowRequiresServiceError(ServiceError):
    """Raised when with_uow decorator is used on a non-Service method."""

    def __init__(self):
        super().__init__("with_uow decorator requires a Service instance as the first argument.")


class WithWowRequiresUowError(ServiceError):
    """Raised when with_uow decorator is used on a Service method without a uow attribute."""

    def __init__(self):
        super().__init__("with_uow decorator requires a Service instance with a uow attribute.")
