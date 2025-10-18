from .definitions import ModelFilterAndSortDefinition
from .exceptions import (
    ModelFiltersFieldNotAllowedError,
    ModelFiltersInvalidFormatError,
    ModelFiltersInvalidOperationError,
    ModelFiltersInvalidSortDirectionError,
    ModelFiltersInvalidSortError,
    ModelFiltersOperationNotAllowedError,
    ModelFiltersSortFieldNotAllowedError,
)
from .models import Filter, FilterOp, Sort

__all__ = ["FiltersAndSortsParser"]


class FiltersAndSortsParser:
    def __init__(
        self,
        definition: ModelFilterAndSortDefinition,
        *,
        raw_filters: list[str] | None = None,
        raw_sorts: list[str] | None = None,
        parse_filters_on_init: bool = True,
        parse_sorts_on_init: bool = True,
        fields_separator: str,
        path_separator: str,
    ):
        self.definition = definition
        self.raw_filters = raw_filters
        self.raw_sorts = raw_sorts
        self.fields_separator = fields_separator
        self.path_separator = path_separator

        self._filters = None
        self._sorts = None

        if parse_filters_on_init:
            _ = self.filters

        if parse_sorts_on_init:
            _ = self.sorts

    @property
    def filters(self) -> list[Filter]:
        if self._filters is None:
            self._filters = self._parse_filters(self.raw_filters)
        return self._filters

    @property
    def sorts(self) -> list[Sort]:
        if self._sorts is None:
            self._sorts = self._parse_sorts(self.raw_sorts)
        return self._sorts

    def add_filter(self, filter_: Filter) -> None:
        self.filters.append(filter_)

    def add_sort(self, sort: Sort) -> None:
        self.sorts.append(sort)

    def add_raw_filter(self, raw_filter: str) -> None:
        self.raw_filters.append(raw_filter)
        self._filters = None

    def add_raw_sort(self, raw_sort: str) -> None:
        self.raw_sorts.append(raw_sort)
        self._sorts = None

    def _parse_filters(self, query_filters: list[str] | None) -> list[Filter]:
        if query_filters is None:
            return []

        filters = []
        for query_filter in query_filters:
            try:
                field, *tokens = query_filter.split(self.fields_separator, maxsplit=2)
                if len(tokens) == 1:
                    op, value = tokens[0], None
                else:
                    op, value = tokens
            except ValueError as e:
                raise ModelFiltersInvalidFormatError(query_filter) from e

            if self.path_separator in field:
                root_field, *path = field.split(self.path_separator)
            else:
                root_field, path = field, None

            if root_field not in self.definition.allowed_filters:
                raise ModelFiltersFieldNotAllowedError(root_field)

            if op not in self.definition.allowed_filters[root_field]:
                raise ModelFiltersOperationNotAllowedError(root_field, op)

            try:
                op = FilterOp(op)
            except ValueError as e:
                raise ModelFiltersInvalidOperationError(field, op) from e

            mapped_field = self.definition.fields_map.get(root_field, root_field)
            full_field = (
                f"{mapped_field}{self.path_separator}{self.path_separator.join(path)}" if path else mapped_field
            )

            filters.append(
                Filter(
                    full_field,
                    FilterOp(op),
                    value,
                    field_type=self.definition.get_field_type(mapped_field, path=path),
                    path_separator=self.path_separator,
                )
            )

        return filters

    def _parse_sorts(self, query_sorts: list[str] | None) -> list[Sort]:
        if query_sorts is None:
            return []

        sorts = []

        for query_sort in query_sorts:
            try:
                if self.fields_separator not in query_sort:
                    field, direction = query_sort, None
                else:
                    field, direction = query_sort.split(self.fields_separator, maxsplit=1)
            except ValueError as e:
                raise ModelFiltersInvalidSortError(query_sort) from e

            if self.path_separator in field:
                root_field, *path = field.split(self.path_separator)
            else:
                root_field, path = field, None

            if root_field not in self.definition.allowed_sorts:
                raise ModelFiltersSortFieldNotAllowedError(root_field)

            if direction is not None and direction not in {"asc", "desc"}:
                raise ModelFiltersInvalidSortDirectionError(direction)

            mapped_field = self.definition.fields_map.get(root_field, root_field)
            full_field = (
                f"{mapped_field}{self.path_separator}{self.path_separator.join(path)}" if path else mapped_field
            )
            sorts.append(Sort(full_field, direction, path_separator=self.path_separator))

        return sorts
