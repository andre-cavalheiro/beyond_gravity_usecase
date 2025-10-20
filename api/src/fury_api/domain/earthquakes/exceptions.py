from fury_api.lib.exceptions import FuryAPIError

__all__ = [
    "EarthquakeError",
    "USGSRateLimitError",
]


class EarthquakeError(FuryAPIError):
    pass


class USGSRateLimitError(EarthquakeError):
    """Raised when the USGS API responds with HTTP 429."""

    def __init__(self, retry_after: str | None = None):
        message = "USGS earthquake service rate limit exceeded"
        super().__init__(message)
        self.retry_after = retry_after
