from fastapi import HTTPException, status

__all__ = ["FuryAPIError", "FuryAPIHTTPError", "UnauthorizedError", "UnauthenticatedError"]


class SingleValidationError:
    loc: list[str]
    msg: str = ""
    type: str = ""

    def __init__(self, loc: list[str], msg: str, type: str):  # noqa: A002
        self.loc = loc
        self.msg = msg
        self.type = type


class FuryValidationError(Exception):
    """Exception type for validation errors."""

    errors: list[SingleValidationError]

    def __init__(self, errors: list[SingleValidationError]):
        self.errors = errors


class FuryAPIError(Exception):
    """Base exception type for Fury API."""


class FuryAPIHTTPError(HTTPException, FuryAPIError):
    """Base exception type for Fury API HTTP exceptions."""

    def __init__(self, status_code: int, detail: str, **kwargs):
        super().__init__(status_code=status_code, detail=detail, **kwargs)


class InternalServerError(FuryAPIError):
    """Exception type for internal server errors."""

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    detail: str = "Internal server error"
    exception: BaseException


class UnauthorizedError(FuryAPIHTTPError):
    """Exception type for unauthorized requests."""

    def __init__(self, detail: str, **kwargs):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail, **kwargs)


class UnauthenticatedError(FuryAPIHTTPError):
    """Exception type for unauthenticated requests."""

    def __init__(self, **kwargs):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail="Requires authentication", **kwargs)
