from datetime import UTC, datetime

__all__ = ["utcnow", "fromisoformat"]


def utcnow() -> datetime:
    """Return current UTC time."""
    return datetime.now(tz=UTC)


def fromisoformat(value: str) -> datetime:
    """Return datetime from ISO format."""
    return datetime.fromisoformat(value)
