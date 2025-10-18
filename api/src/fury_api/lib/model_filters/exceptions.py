__all__ = [
    "ModelFiltersError",
    "ModelFiltersFilterError",
    "ModelFiltersInvalidFormatError",
    "ModelFiltersFieldNotAllowedError",
    "ModelFiltersOperationNotAllowedError",
    "ModelFiltersInvalidOperationError",
    "ModelFiltersSortError",
    "ModelFiltersInvalidSortError",
    "ModelFiltersSortFieldNotAllowedError",
    "ModelFiltersInvalidSortDirectionError",
    "FilterInvalidTypeError",
]


class ModelFiltersError(Exception):
    """Base class for model filters exceptions."""


class ModelFiltersFilterError(ModelFiltersError):
    """Raised when there is an error parsing the filter params."""


class ModelFiltersInvalidFormatError(ModelFiltersFilterError):
    """Raised when the filter has an invalid format."""

    def __init__(self, value: str) -> None:
        super().__init__(f"Invalid filter format {value!r}")


class ModelFiltersFieldNotAllowedError(ModelFiltersFilterError):
    """Raised when a filter field is not allowed."""

    def __init__(self, field: str) -> None:
        super().__init__(f"Filter field {field!r} not allowed")


class ModelFiltersOperationNotAllowedError(ModelFiltersFilterError):
    """Raised when a filter operation is not allowed for a field."""

    def __init__(self, field: str, op: str) -> None:
        super().__init__(f"Filter operation {op!r} not allowed for field {field!r}")


class ModelFiltersInvalidOperationError(ModelFiltersFilterError):
    """Raised when a filter operation is invalid for a field."""

    def __init__(self, field: str, op: str) -> None:
        super().__init__(f"Invalid operation {op!r} for field {field!r}")


class ModelFiltersSortError(ModelFiltersError):
    """Raised when there is an error parsing the sort params."""


class ModelFiltersInvalidSortError(ModelFiltersSortError):
    """Raised when the sort params are invalid."""

    def __init__(self, value: str) -> None:
        super().__init__(f"Invalid sort format {value!r}")


class ModelFiltersSortFieldNotAllowedError(ModelFiltersSortError):
    """Raised when a sort field is not allowed."""

    def __init__(self, field: str) -> None:
        super().__init__(f"Sort field {field!r} not allowed")


class ModelFiltersInvalidSortDirectionError(ModelFiltersSortError):
    """Raised when a sort direction is invalid."""

    def __init__(self, direction: str) -> None:
        super().__init__(f"Invalid sort direction {direction!r}")


class FilterInvalidTypeError(ModelFiltersError):
    """Raised when a filter value has an invalid type."""

    def __init__(self, field: str, value: str, field_type: type) -> None:
        super().__init__(f"Invalid type for filter {field!r} value {value!r}, expected {field_type.__name__!r}")
