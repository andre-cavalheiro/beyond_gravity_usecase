from starlette.middleware.cors import CORSMiddleware

from .settings import config

__all__ = ["middleware_config"]


middleware_config = {
    "middleware_class": CORSMiddleware,
    "allow_origins": config.api.CORS_ORIGINS,
    "allow_methods": config.api.CORS_METHODS,
    "allow_headers": config.api.CORS_HEADERS,
}
