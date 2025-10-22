from collections.abc import Callable

from fastapi import HTTPException, Query, status

from fury_api.lib.model_filters import ModelFilterAndSortDefinition, ModelFiltersError
from fury_api.lib.model_filters.parsers import FiltersAndSortsParser

__all__ = [
    "get_models_filters_parser_factory",
]


def get_models_filters_parser_factory(
    filters_definition: ModelFilterAndSortDefinition,
    *,
    init: bool = True,
    fields_separator: str = ":",
    path_separator: str = "/",
    additional_filters: list[str] | None = None,
    additional_sorts: list[str] | None = None,
) -> Callable[..., FiltersAndSortsParser]:
    def dependency(
        filters: list[str] | None = Query(None, alias="filters"), sorts: list[str] | None = Query(None, alias="sorts")
    ) -> FiltersAndSortsParser:
        try:
            return FiltersAndSortsParser(
                filters_definition,
                raw_filters=(filters or []) + (additional_filters or []),
                raw_sorts=(sorts or []) + (additional_sorts or []),
                parse_filters_on_init=init,
                parse_sorts_on_init=init,
                fields_separator=fields_separator,
                path_separator=path_separator,
            )
        except ModelFiltersError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    return dependency
