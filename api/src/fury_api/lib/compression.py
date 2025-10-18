from fastapi.middleware.gzip import GZipMiddleware

__all__ = ["middleware_config"]


middleware_config = {"middleware_class": GZipMiddleware, "minimum_size": 500, "compresslevel": 9}
