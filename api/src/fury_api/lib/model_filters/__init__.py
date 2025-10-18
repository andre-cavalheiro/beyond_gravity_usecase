from datetime import datetime

from sqlmodel import SQLModel

from .definitions import ModelFilterAndSortDefinition, try_get_field_type
from .exceptions import ModelFiltersError
from .models import Filter, FilterOp, Sort
from .parsers import FiltersAndSortsParser

__all__ = [
    "ModelFilterAndSortDefinition",
    "Filter",
    "FilterOp",
    "Sort",
    "ModelFilter",
    "ModelSort",
    "ModelFiltersError",
    "FiltersAndSortsParser",
    "get_default_ops_for_type",
    "is_op_supported",
    "try_get_field_type",
    "translate_filters",
    "translate_sorts",
]

ModelFilter = Filter
ModelSort = Sort


def get_default_ops_for_type(type_: type) -> set[FilterOp]:
    default_ops = _DEFAULT_OPS_MAP.get(type_)
    if default_ops is not None:
        return default_ops
    for base_type, ops in _DEFAULT_OPS_MAP.items():
        if issubclass(type_, base_type):
            return ops
    return set()


def is_op_supported(type_: type, op: FilterOp) -> bool:
    return op in get_default_ops_for_type(type_)


_common_ops = {FilterOp.EQ, FilterOp.NEQ, FilterOp.IN, FilterOp.NOT_IN, FilterOp.ISNULL, FilterOp.ISNOTNULL}
_DEFAULT_OPS_MAP = {
    list: {FilterOp.CONTAINS, FilterOp.NOT_CONTAINS, FilterOp.CONTAINS_ONE_OF},
    # Currently we only support filtering path fields as strings
    dict: {
        *_common_ops,
        FilterOp.LIKE,
        FilterOp.ILIKE,
        FilterOp.CONTAINS,
        FilterOp.NOT_CONTAINS,
    },
    str: {*_common_ops, FilterOp.LIKE, FilterOp.ILIKE, FilterOp.CONTAINS, FilterOp.NOT_CONTAINS},
    int: {*_common_ops, FilterOp.LT, FilterOp.LTE, FilterOp.GT, FilterOp.GTE},
    float: {*_common_ops, FilterOp.LT, FilterOp.LTE, FilterOp.GT, FilterOp.GTE},
    bool: _common_ops,
    datetime: {*_common_ops, FilterOp.LT, FilterOp.LTE, FilterOp.GT, FilterOp.GTE},
}


def translate_filters(
    model_filters: list[Filter] | None,
    field_translations: dict[str, str],
    model: type[SQLModel],
    *,
    fields_types: dict[str, type] | None = None,
) -> list[Filter]:
    fields_types = fields_types or {}
    translated_filters = []
    for model_filter in model_filters or []:
        new_field = field_translations.get(model_filter.field, model_filter.field)
        field_type = fields_types.get(model_filter.field)
        if new_field != model_filter.field:
            model_filter.field = new_field
            if len(model_filter.sub_path) > 0:
                model_filter.field += model_filter.path_separator + model_filter.sub_path
        elif field_type is None:
            # TODO: should this always run to ensure the field type is correct?
            model_filter.field_type = try_get_field_type(model, model_filter.field)
        if field_type is not None:
            model_filter.field_type = field_type
            model_filter.force_attr_cast = True
        model_filter.__post_init__()
        translated_filters.append(model_filter)
    return translated_filters


def translate_sorts(model_sorts: list[Sort] | None, field_translations: dict[str, str]) -> list[Sort]:
    translated_sorts = []
    for model_sort in model_sorts or []:
        new_field = field_translations.get(model_sort.field, model_sort.field)
        if new_field != model_sort.field:
            model_sort.field = new_field
            model_sort.__post_init__()
        translated_sorts.append(model_sort)
    return translated_sorts
