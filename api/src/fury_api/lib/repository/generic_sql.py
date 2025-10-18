from abc import ABC
from collections.abc import Iterable, Sequence
from typing import Any, Generic, TypeVar

from fastapi_pagination.ext.sqlalchemy import paginate
from sqlalchemy import Select, or_, select, text, func
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from fury_api.lib.pagination import CursorPage

__all__ = ["GenericSqlRepository"]


T = TypeVar("T", bound=SQLModel)


class GenericSqlRepository(Generic[T], ABC):
    def __init__(self, model_cls: type[T], id_attr: str | None = None) -> None:
        self._model_cls = model_cls
        self._id_attr = id_attr or getattr(model_cls, "__id_attr__", "id")

    async def add(self, session: AsyncSession, record: T) -> T:
        session.add(record)
        await session.flush()
        await session.refresh(record)
        return record

    async def get_by_id(self, session: AsyncSession, id_: Any) -> T | None:
        q = select(self._model_cls).where(getattr(self._model_cls, self._id_attr) == id_)
        result = await session.exec(q)
        return result.scalar_one_or_none()

    async def list_with_pagination(
        self,
        session: AsyncSession,
        filters: dict[str, Any] | None = None,
        advanced_filters: Sequence[Any] | None = None,
        desc: bool = False,
        search_query: str | None = None,
        *,
        query: Select | None = None,
    ) -> CursorPage[T]:
        q = query if query is not None else select(self._model_cls)
        if desc:
            q = q.order_by(getattr(self._model_cls, self._id_attr).desc())
        else:
            q = q.order_by(getattr(self._model_cls, self._id_attr))

        if filters:
            q = q.filter_by(**filters)
        if advanced_filters:
            q = q.where(or_(*advanced_filters))
        if search_query:
            q = await self._apply_search_query(q, search_query)

        return await paginate(session, q)

    async def list(
        self,
        session: AsyncSession,
        *,
        query: Select | None = None,
        filters: dict[str, Any] | None = None,
        advanced_filters: Sequence[Any] | None = None,
        search_query: str | None = None,
    ) -> list[T]:
        q = query if query is not None else select(self._model_cls)
        q = q.order_by(getattr(self._model_cls, self._id_attr))
        if filters:
            q = q.filter_by(**filters)
        if advanced_filters:
            q = q.where(or_(*advanced_filters))
        if search_query:
            q = await self._apply_search_query(q, search_query)

        result = await session.exec(q)
        return result.scalars().all()

    async def update(self, session: AsyncSession, record: T) -> T:
        session.add(record)
        await session.flush()
        await session.refresh(record)
        return record

    async def delete(self, session: AsyncSession, id_: Any) -> T | None:
        q = select(self._model_cls).where(getattr(self._model_cls, self._id_attr) == id_)
        result = await session.exec(q)
        record = result.scalar_one_or_none()
        if record:
            await session.delete(record)
            await session.flush()
        return record

    async def delete_many(self, session: AsyncSession, records: Sequence[T]) -> Sequence[T]:
        for record in records:
            await session.delete(record)
        await session.flush()
        return records

    async def list_by_ids(self, session: AsyncSession, ids: Iterable[Any]) -> Iterable[T]:
        id_attr = getattr(self._model_cls, self._id_attr)  # Use the dynamic ID attribute
        q = select(self._model_cls).where(id_attr.in_(ids))  # Construct the query with the dynamic ID attribute
        result = await session.exec(q)
        return result.scalars().all()

    @classmethod
    async def execute_raw(cls, session: AsyncSession, query: str) -> Any:
        result = await session.execute(text(query))
        return result.scalars().one_or_none()

    async def _apply_search_query(self, query: Select, search_query: str) -> Select:
        filters = []

        # Check if the model has a search_vector attribute and apply full-text search
        if hasattr(self._model_cls, "search_vector"):
            ts_query = func.plainto_tsquery("english", search_query)
            filters.append(self._model_cls.search_vector.op("@@")(ts_query))

        # Check if the model has a title attribute and apply ILIKE search
        if hasattr(self._model_cls, "title"):
            filters.append(self._model_cls.title.ilike(f"%{search_query}%"))

        # Check if the model has an id attribute and add to the filters
        if hasattr(self._model_cls, "id"):
            filters.append(self._model_cls.id.ilike(f"%{search_query}%"))

        # Check if the model has a blueprint_id attribute and add to the filters
        if hasattr(self._model_cls, "blueprint_id"):
            filters.append(self._model_cls.blueprint_id.ilike(f"%{search_query}%"))

        if not filters:
            raise NotImplementedError(f"Search functionality is not implemented for {self._model_cls.__name__}")

        # Apply OR condition for all the filters
        query = query.where(or_(*filters))
        return query
