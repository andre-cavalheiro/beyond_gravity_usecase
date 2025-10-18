from __future__ import annotations

from contextlib import contextmanager
from typing import Generic

from fastapi.params import Query
from fastapi_pagination import set_page
from fastapi_pagination.bases import AbstractParams, CursorRawParams
from fastapi_pagination.cursor import Cursor, T, decode_cursor
from fastapi_pagination.cursor import CursorPage as BaseCursorPage
from fastapi_pagination.cursor import CursorParams as BaseCursorParams

__all__ = ["CursorPage", "CursorParams", "cursor_page"]


class CursorParams(BaseCursorParams):
    include_total: bool = Query(False, description="Include total items", alias="includeTotal")

    def to_raw_params(self) -> CursorRawParams:
        return CursorRawParams(
            cursor=decode_cursor(self.cursor, to_str=self.str_cursor), size=self.size, include_total=self.include_total
        )


class CursorPage(BaseCursorPage[T], Generic[T]):
    __params_type__ = CursorParams

    @classmethod
    def create(
        cls,
        items: list[T],
        params: AbstractParams,
        *,
        current: Cursor = None,
        current_backwards: Cursor = None,
        next_: Cursor = None,
        previous: Cursor = None,
        total: int | None = None,
        **kwargs,
    ) -> "CursorPage[T]":
        return super().create(
            items,
            params,
            current=current,
            current_backwards=current_backwards,
            next_=next_,
            previous=previous,
            total=total,
            **kwargs,
        )


@contextmanager
def cursor_page(page: type[CursorPage], original_page: type[CursorPage] | None = None) -> None:
    try:
        set_page(page)
        yield
    finally:
        set_page(original_page)
