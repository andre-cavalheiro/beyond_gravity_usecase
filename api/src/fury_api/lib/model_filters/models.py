import contextlib
from collections.abc import Callable, Generator
from dataclasses import asdict, dataclass
from dataclasses import field as dataclass_field
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Literal

from .exceptions import FilterInvalidTypeError

__all__ = ["Filter", "FilterOp", "Sort"]


class FilterOp(str, Enum):
    EQ = "eq"
    NEQ = "neq"

    LT = "lt"
    LTE = "lte"

    GT = "gt"
    GTE = "gte"

    IN = "in"
    NOT_IN = "notIn"

    LIKE = "like"
    NOT_LIKE = "notLike"
    ILIKE = "ilike"
    NOT_ILIKE = "notILike"

    CONTAINS = "contains"
    NOT_CONTAINS = "notContains"

    CONTAINS_ONE_OF = "containsOneOf"

    ISNULL = "isnull"
    ISNOTNULL = "isnotnull"

    def can_use_value_list(self) -> bool:
        return self in {
            FilterOp.IN,
            FilterOp.NOT_IN,
            FilterOp.CONTAINS,
            FilterOp.NOT_CONTAINS,
            FilterOp.CONTAINS_ONE_OF,
        }


@dataclass(slots=True)
class Sort:
    field: str
    direction: Literal["asc", "desc"] | None = None
    path_separator: str = "/"
    path_fields: list[str] = dataclass_field(init=False, default_factory=list)
    force_type_cast: type | None = None
    custom_order_mapping: dict[Any, Any] | None = None

    def __post_init__(self) -> None:
        """Split field into path fields if it contains the path separator."""
        if self.path_separator in self.field:
            self.field, *self.path_fields = self.field.split(self.path_separator)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class Filter:
    field: str
    op: FilterOp
    value: Any
    field_type: type | None = None
    validate_types: bool = True
    path_separator: str = "/"
    value_split_separator = ","
    path_fields: list[str] = dataclass_field(init=False, default_factory=list)
    original_value: Any = dataclass_field(init=False)
    force_attr_cast: bool = False

    def __post_init__(self) -> None:
        """Split field into path fields if it contains the path separator. Validate types if enabled."""
        self.original_value = self.value

        if self.path_separator in self.field:
            self.field, *self.path_fields = self.field.split(self.path_separator)

        if self.field_type is None:
            # Assume str type if not provided
            self.field_type = str

        if self.validate_types:
            self._type_validation()

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def is_path(self) -> bool:
        return len(self.path_fields) > 0

    @property
    def sub_path(self) -> str:
        return self.path_separator.join(self.path_fields)

    def can_use_value_list(self) -> bool:
        return self.op.can_use_value_list()

    def _type_validation(self) -> None:
        if self.field_type is None:
            return

        if self.op in {FilterOp.ISNULL, FilterOp.ISNOTNULL}:
            return

        validator_ = get_type_validator(self.field_type)
        if validator_ is None:
            raise FilterInvalidTypeError(self.field, self.value, self.field_type)

        self.value = validator_(self, self.value)


@dataclass(frozen=True, slots=True)
class TypeValidator:
    field_type: type
    validator: Callable[[Filter, Any], Any]
    allow_split_value: bool = True

    def __call__(self, filter_: Filter, value: Any) -> Any:
        try:
            if self.allow_split_value and filter_.can_use_value_list():
                return [
                    self.validator(filter_, v)
                    for v in self.value_split_iterator(value, separator=filter_.value_split_separator)
                ]
        except FilterInvalidTypeError:
            pass
        if isinstance(value, self.field_type):
            return value
        if isinstance(value, list):
            return [self.validator(filter_, v) for v in value]

        return self.validator(filter_, value)

    def value_split_iterator(self, value: Any, separator) -> Generator[Any, None, None]:
        if isinstance(value, list):
            yield from value
        elif not self.allow_split_value:
            yield value
        elif isinstance(value, str):
            yield from value.split(separator)
        else:
            yield value


_type_validators: dict[type, TypeValidator] = None


def get_type_validator(field_type: type | None) -> TypeValidator | None:
    global _type_validators
    if _type_validators is None:
        _type_validators = {
            int: TypeValidator(int, _validate_int),
            float: TypeValidator(float, _validate_float),
            str: TypeValidator(str, _validate_str),
            datetime: TypeValidator(datetime, _validate_datetime),
            bool: TypeValidator(bool, _validate_bool, allow_split_value=False),
            # No validation for these types
            dict: TypeValidator(dict, lambda filter_, value: value),
            list: TypeValidator(list, lambda filter_, value: value),
        }

    validator_ = _type_validators.get(field_type)
    if validator_ is None:
        for _type, validator_ in _type_validators.items():
            if issubclass(field_type, _type):
                return validator_
    return validator_


def _validate_int(filter_: Filter, value: Any) -> int:
    if isinstance(value, int):
        return value
    try:
        return int(value)
    except (ValueError, TypeError) as e:
        raise FilterInvalidTypeError(filter_.field, value, filter_.field_type) from e


def _validate_float(filter_: Filter, value: Any) -> float:
    if isinstance(value, float):
        return value
    try:
        return float(value)
    except (ValueError, TypeError) as e:
        raise FilterInvalidTypeError(filter_.field, value, filter_.field_type) from e


def _validate_str(filter_: Filter, value: Any) -> list[str] | str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return [str(v) for v in value]
    return str(value)


def _validate_bool(filter_: Filter, value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        if value.lower() in {"true", "yes", "1", "y"}:
            return True
        if value.lower() in {"false", "no", "0", "n"}:
            return False
    if isinstance(value, int):
        return value == 1
    raise FilterInvalidTypeError(filter_.field, value, filter_.field_type)


def _validate_datetime(filter_: Filter, value: Any) -> datetime:
    if isinstance(value, datetime):
        return value

    with contextlib.suppress(ValueError, TypeError):
        return datetime.fromisoformat(value)

    with contextlib.suppress(ValueError, TypeError):
        return datetime.fromtimestamp(float(value) * 1000, tz=UTC)

    with contextlib.suppress(ValueError, TypeError):
        return datetime.fromtimestamp(float(value), tz=UTC)

    for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d"]:
        with contextlib.suppress(ValueError, TypeError):
            return datetime.strptime(value, fmt).replace(tzinfo=UTC)

    raise FilterInvalidTypeError(filter_.field, value, filter_.field_type)
