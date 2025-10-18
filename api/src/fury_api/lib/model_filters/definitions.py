from sqlmodel import SQLModel

from .models import FilterOp

__all__ = ["ModelFilterAndSortDefinition", "try_get_field_type"]


def try_get_field_type(model: type[SQLModel], field: str, path: list[str] | None = None) -> type | None:
    attr = getattr(model, field, None)
    if attr is None:
        return None

    if path is not None:
        # Unable to get type for nested fields
        return None

    type_ = getattr(attr, "type", None)
    if type_ is None:
        return None
    while type_ is not None:
        try:
            return type_.python_type
        except Exception:  # noqa: BLE001
            type_ = getattr(type_, "impl", None)
    return None


class ModelFilterAndSortDefinition:
    def __init__(
        self,
        model: type[SQLModel],
        allowed_filters: dict[str, set[FilterOp]],
        allowed_sorts: set[str],
        *,
        custom_fields_map: dict[str, str] | None = None,
        enable_model_aliases: bool = True,
    ):
        self.model = model
        self.allowed_filters = allowed_filters or {}
        self.allowed_sorts = set(allowed_sorts or [])

        self.fields_map = custom_fields_map or {}
        self._enable_model_aliases = enable_model_aliases

        if self._enable_model_aliases:
            self._create_aliases_map()

    def get_field_type(self, field: str, path: list[str] | None = None) -> type | None:
        if field in self.fields_map:
            field = self.fields_map[field]

        return try_get_field_type(self.model, field, path)

    def _create_aliases_map(self) -> None:
        filters_updates = {}
        for filter_field, allowed_ops in self.allowed_filters.items():
            if filter_field in self.fields_map:
                continue

            model_field = self.model.__fields__.get(filter_field)
            alias = model_field.alias if model_field is not None else None
            if alias is None:
                continue

            if alias not in self.fields_map:
                self.fields_map[alias] = filter_field

            if alias not in self.allowed_filters:
                filters_updates[alias] = allowed_ops
        self.allowed_filters.update(filters_updates)

        sorts_updates = set()
        for sort_field in self.allowed_sorts:
            if sort_field in self.fields_map:
                continue

            model_field = self.model.__fields__.get(sort_field)
            alias = model_field.alias if model_field is not None else None
            if alias is None:
                continue

            if alias not in self.fields_map:
                self.fields_map[alias] = filter_field

            if alias not in self.allowed_sorts:
                sorts_updates.add(alias)
        self.allowed_sorts.update(sorts_updates)
