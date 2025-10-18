from abc import ABC
from collections.abc import Sequence
from datetime import datetime
from typing import Any, ClassVar, Optional, List

from sqlalchemy import TIMESTAMP, BigInteger, Boolean, Float, Select, String, case, cast, func, select

from sqlmodel.ext.asyncio.session import AsyncSession

from fury_api.lib.model_filters import Filter, FilterOp, Sort
from fury_api.lib.pagination import CursorPage
from fury_api.lib.repository.generic_sql import GenericSqlRepository, T

__all__ = ["GenericSqlExtendedRepository", "ModelFilter", "ModelSort"]

ModelFilter = Filter
ModelSort = Sort


class GenericSqlExtendedRepository(GenericSqlRepository[T], ABC):
    def _apply_model_filters(self, query: Select, filters: list[Filter]) -> Select:
        return SqlFilterAdapter.apply_all(self, query, filters)

    def _apply_model_sorts(self, query: Select, sorts: list[Sort]) -> Select:
        return SqlSortAdapter.apply_all(self, query, sorts)

    def _build_query(
        self, query: Select | None, *, model_filters: list[Filter] | None, model_sorts: list[Sort] | None
    ) -> Select:
        if query is None:
            query = select(self._model_cls)
        if model_filters:
            query = self._apply_model_filters(query, model_filters)
        if model_sorts:
            query = self._apply_model_sorts(query, model_sorts)
        return query

    async def list_with_pagination(
        self,
        session: AsyncSession,
        filters: dict[str, Any] | None = None,
        advanced_filters: Sequence[Any] | None = None,
        *,
        query: Select | None = None,
        model_filters: list[Filter] | None = None,
        model_sorts: list[Sort] | None = None,
        search_query: str | None = None,
    ) -> CursorPage[T]:
        q = self._build_query(query, model_filters=model_filters, model_sorts=model_sorts)
        return await super().list_with_pagination(
            session, filters=filters, advanced_filters=advanced_filters, query=q, search_query=search_query
        )

    async def list(
        self,
        session: AsyncSession,
        *,
        query: Select | None = None,
        filters: dict[str, Any] | None = None,
        advanced_filters: Sequence[Any] | None = None,
        model_filters: list[Filter] | None = None,
        model_sorts: list[Sort] | None = None,
        search_query: str | None = None,
    ) -> list[T]:
        q = self._build_query(query, model_filters=model_filters, model_sorts=model_sorts)
        return await super().list(
            session, query=q, filters=filters, advanced_filters=advanced_filters, search_query=search_query
        )

    async def count(
        self,
        session: AsyncSession,
        *,
        query: Select | None = None,
        model_filters: Optional[List[Filter]] = None,
    ) -> int:
        """
        Counts all items in the database matching the provided filters.

        :param session: AsyncSession for database interaction.
        :param query: Optional base query.
        :param model_filters: Optional list of filters to apply.
        :return: The count of matching items.
        """
        q = self._build_query(query, model_filters=model_filters, model_sorts=None)
        count_query = select(func.count()).select_from(q.subquery())
        result = await session.execute(count_query)
        return result.scalar()

    async def update_by_id(
        self,
        session: AsyncSession,
        entity_id: Any,
        updates: dict[str, Any],
        *,
        commit: bool = True,
    ) -> T:
        """
        Generic update method to modify a single entity by ID.

        :param session: AsyncSession to use
        :param entity_id: The primary key of the entity to update
        :param updates: A dict of fields to update
        :param commit: Whether to commit after updating
        :return: The updated entity
        """
        # Step 1: Fetch the object
        statement = select(self._model_cls).where(self._model_cls.id == entity_id)
        result = await session.execute(statement)
        instance = result.scalar_one_or_none()

        if not instance:
            raise ValueError(f"{self._model_cls.__name__} with id={entity_id} not found")

        # Step 2: Apply updates
        for key, value in updates.items():
            if hasattr(instance, key):
                setattr(instance, key, value)
            else:
                raise AttributeError(f"{self._model_cls.__name__} has no attribute '{key}'")

        # Step 3: Persist
        session.add(instance)
        if commit:
            await session.commit()
        else:
            await session.flush()

        return instance


class SqlAdapter:
    @classmethod
    def cast(cls, value: Any, type_: type) -> Any:
        default_cast_type = String
        if type_ is str:
            db_type = String
        elif type_ is bool:
            db_type = Boolean
        elif type_ is int:
            db_type = BigInteger
        elif type_ is float:
            db_type = Float
        elif type_ is datetime:
            db_type = TIMESTAMP(timezone=True)
        else:
            db_type = default_cast_type
        return cast(value, db_type)

    @classmethod
    def _safe_cast_attr(cls, attr: Any) -> Any:
        return cls.cast(attr, String)

    @classmethod
    def _safe_cast_value(cls, value: Any) -> Any:
        return cls.cast(value, String)


class SqlFilterAdapter(SqlAdapter):
    OPS_MAP: ClassVar[dict[FilterOp, str]] = {op: op.value.lower() for op in FilterOp} | {FilterOp.IN: "in_"}

    @classmethod
    def _get_attr(cls, repo: GenericSqlRepository[T], filter_: Filter) -> Any:
        return getattr(repo._model_cls, filter_.field)

    @classmethod
    def _get_attr_and_value(
        cls, repo: GenericSqlRepository[T], filter_: Filter, *, use_list: bool = False
    ) -> tuple[Any, Any]:
        def inner() -> tuple[Any, Any]:
            attr = cls._get_attr(repo, filter_)

            if filter_.field_type is not None:
                # Check if same type
                if isinstance(filter_.value, filter_.field_type):
                    return attr, filter_.value

                # Check if can use list and value is list
                if filter_.can_use_value_list() and isinstance(filter_.value, list):
                    if all(isinstance(v, filter_.field_type) for v in filter_.value):
                        return attr, filter_.value

                    # Cast each value of the list to String for safe comparison since they're not all the same type
                    return cls._safe_cast_attr(attr), [cls._safe_cast_value(v) for v in filter_.value]

            if filter_.can_use_value_list() and isinstance(filter_.value, str):
                return cls._safe_cast_attr(attr), filter_.value.split(filter_.value_split_separator)

            # If no valid comparison, cast both to String and compare
            return cls._safe_cast_attr(attr), cls._safe_cast_value(filter_.value)

        attr, value = inner()

        if filter_.force_attr_cast:
            attr = cls.cast(attr, filter_.field_type)

        if use_list and not isinstance(value, list):
            value = [value]
        return attr, value

    @classmethod
    def apply_all(cls, repo: GenericSqlRepository[T], query: Select, filters: list[Filter]) -> Select:
        for filter_ in filters:
            query = cls.apply(repo, query, filter_)
        return query

    @classmethod
    def apply(cls, repo: GenericSqlRepository[T], query: Select, filter_: Filter) -> Select:
        if filter_.is_path:
            return SqlFilterPathAdapter.apply(repo, query, filter_)

        try:
            func = getattr(cls, cls.OPS_MAP.get(filter_.op))
        except (AttributeError, TypeError) as e:
            raise NotImplementedError(f"Filter operation {filter_.op} not implemented") from e

        return func(repo, query, filter_)

    @classmethod
    def eq(cls, repo: GenericSqlRepository[T], query: Select, filter_: Filter) -> Select:
        attr, value = cls._get_attr_and_value(repo, filter_)
        return query.where(attr == value)

    @classmethod
    def neq(cls, repo: GenericSqlRepository[T], query: Select, filter_: Filter) -> Select:
        attr, value = cls._get_attr_and_value(repo, filter_)
        return query.where(attr != value)

    @classmethod
    def lt(cls, repo: GenericSqlRepository[T], query: Select, filter_: Filter) -> Select:
        attr, value = cls._get_attr_and_value(repo, filter_)
        return query.where(attr < value)

    @classmethod
    def lte(cls, repo: GenericSqlRepository[T], query: Select, filter_: Filter) -> Select:
        attr, value = cls._get_attr_and_value(repo, filter_)
        return query.where(attr <= value)

    @classmethod
    def gt(cls, repo: GenericSqlRepository[T], query: Select, filter_: Filter) -> Select:
        attr, value = cls._get_attr_and_value(repo, filter_)
        return query.where(attr > value)

    @classmethod
    def gte(cls, repo: GenericSqlRepository[T], query: Select, filter_: Filter) -> Select:
        attr, value = cls._get_attr_and_value(repo, filter_)
        return query.where(attr >= value)

    @classmethod
    def in_(cls, repo: GenericSqlRepository[T], query: Select, filter_: Filter) -> Select:
        attr, value = cls._get_attr_and_value(repo, filter_, use_list=True)
        if not isinstance(value, list):
            value = [value]
        return query.where(attr.in_(value))

    @classmethod
    def notin(cls, repo: GenericSqlRepository[T], query: Select, filter_: Filter) -> Select:
        attr, value = cls._get_attr_and_value(repo, filter_, use_list=True)
        if not isinstance(value, list):
            value = [value]
        return query.where(~attr.in_(value))

    @classmethod
    def like(cls, repo: GenericSqlRepository[T], query: Select, filter_: Filter) -> Select:
        attr, value = cls._get_attr_and_value(repo, filter_)
        return query.where(attr.like(value))

    @classmethod
    def ilike(cls, repo: GenericSqlRepository[T], query: Select, filter_: Filter) -> Select:
        attr, value = cls._get_attr_and_value(repo, filter_)
        return query.where(attr.ilike(value))

    @classmethod
    def notlike(cls, repo: GenericSqlRepository[T], query: Select, filter_: Filter) -> Select:
        attr, value = cls._get_attr_and_value(repo, filter_)
        return query.where(~attr.like(value))

    @classmethod
    def notilike(cls, repo: GenericSqlRepository[T], query: Select, filter_: Filter) -> Select:
        attr, value = cls._get_attr_and_value(repo, filter_)
        return query.where(~attr.ilike(value))

    @classmethod
    def contains(cls, repo: GenericSqlRepository[T], query: Select, filter_: Filter) -> Select:
        attr, value = cls._get_attr_and_value(repo, filter_, use_list=True)

        if isinstance(value, list):
            # Use PostgreSQL array operator `@>` for array containment
            return query.where(attr.op("@>")(func.cast(value, attr.type)))

        return query.where(attr.contains(value))

    @classmethod
    def notcontains(cls, repo: GenericSqlRepository[T], query: Select, filter_: Filter) -> Select:
        attr, value = cls._get_attr_and_value(repo, filter_)
        return query.where(~attr.contains(value))

    @classmethod
    def isnull(cls, repo: GenericSqlRepository[T], query: Select, filter_: Filter) -> Select:
        attr, _ = cls._get_attr_and_value(repo, filter_)
        return query.where(attr.is_(None))

    @classmethod
    def isnotnull(cls, repo: GenericSqlRepository[T], query: Select, filter_: Filter) -> Select:
        attr, _ = cls._get_attr_and_value(repo, filter_)
        return query.where(attr.is_not(None))

    @classmethod
    def containsoneof(cls, repo: GenericSqlRepository[T], query: Select, filter_: Filter) -> Select:
        attr, value = cls._get_attr_and_value(repo, filter_, use_list=True)

        # Ensure both attr and value are lists
        if not isinstance(value, list):
            raise Exception("Target Value must be list")  # TODO: this should be a proper exception

        # SQL equivalent logic: attr overlaps with the provided list
        # This assumes a PostgreSQL-style implementation using the `any` or `overlaps` operator.
        return query.where(attr.overlap(value))


class SqlFilterPathAdapter(SqlFilterAdapter):
    # Add overrides for ops handlers
    OPS_MAP: ClassVar[dict[FilterOp, str]] = SqlFilterAdapter.OPS_MAP

    @classmethod
    def _get_attr(cls, repo: GenericSqlRepository[T], filter_: Filter) -> Any:
        attr = getattr(repo._model_cls, filter_.field)
        if filter_.is_path:
            for field in filter_.path_fields:
                attr = attr[field]
        # Currently we only support filtering path fields as strings
        return attr.astext

    @classmethod
    def _safe_cast_attr(cls, attr: Any) -> Any:
        # Currently we only support filtering path fields as strings
        return attr

    @classmethod
    def apply(cls, repo: GenericSqlRepository[T], query: Select, filter_: Filter) -> Select:
        func = getattr(cls, cls.OPS_MAP.get(filter_.op))
        if func is None:
            raise NotImplementedError(f"Filter operation {filter_.op} not implemented for path filters")
        return func(repo, query, filter_)


class SqlSortAdapter(SqlAdapter):
    @classmethod
    def _get_attr(cls, repo: GenericSqlRepository[T], sort: Sort) -> Any:
        attr = getattr(repo._model_cls, sort.field)
        if not sort.path_fields:
            return attr
        for field in sort.path_fields:
            attr = attr[field]
        return attr.astext

    @classmethod
    def apply_all(cls, repo: GenericSqlRepository[T], query: Select, sorts: list[Sort]) -> Select:
        for sort in sorts:
            query = cls.apply(repo, query, sort)
        return query

    @classmethod
    def apply(cls, repo: GenericSqlRepository[T], query: Select, sort: Sort) -> Select:
        attr = cls._get_attr(repo, sort)

        if sort.custom_order_mapping is not None:
            attr = case(sort.custom_order_mapping, value=attr)

        if sort.direction is None:
            return query.order_by(attr)
        return query.order_by(getattr(attr, sort.direction)())
