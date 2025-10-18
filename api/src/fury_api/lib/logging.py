import logging
from typing import Any

import msgspec
import structlog

from .settings import config as conf

__all__ = ["configure", "get_logger", "Logger"]


class Logger:
    """Wrapper for logger that implements the same interface as structlog.BoundLogger.

    This allows supporting multiple logging backends without having to change the code that uses the logger.
    (e.g. stdlib, structlog, etc.)
    """

    def __init__(self, logger: Any):
        self._has_bind = hasattr(logger, "bind")
        self._logger = logger

    def bind(self, **kwargs: Any) -> "Logger":
        if self._has_bind:
            return Logger(self._logger.bind(**kwargs))
        return self

    def debug(self, *args: Any, **kwargs: Any) -> None:
        self._logger.debug(*args, **kwargs)

    def info(self, *args: Any, **kwargs: Any) -> None:
        self._logger.info(*args, **kwargs)

    def warning(self, *args: Any, **kwargs: Any) -> None:
        self._logger.warning(*args, **kwargs)

    def error(self, *args: Any, **kwargs: Any) -> None:
        self._logger.error(*args, **kwargs)

    def critical(self, *args: Any, **kwargs: Any) -> None:
        self._logger.critical(*args, **kwargs)

    def exception(self, *args: Any, **kwargs: Any) -> None:
        self._logger.exception(*args, **kwargs)


def _configure_structlog_logging() -> None:
    _processors = (
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.add_log_level,
        structlog.processors.format_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
        (
            structlog.processors.CallsiteParameterAdder(
                {
                    structlog.processors.CallsiteParameter.FILENAME,
                    structlog.processors.CallsiteParameter.FUNC_NAME,
                    structlog.processors.CallsiteParameter.LINENO,
                }
            )
            if conf.app.DEBUG
            else None
        ),
        structlog.processors.UnicodeDecoder(),
        (
            structlog.dev.ConsoleRenderer()
            if conf.logging.FORMAT == "console"
            else structlog.processors.JSONRenderer(serializer=msgspec.json.encode)
        ),
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
    )
    structlog.configure(
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        processors=[p for p in _processors if p],
    )


def _configure_loggers() -> None:
    formatter = logging.Formatter(conf.logging.FORMAT_EXTERNAL)
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    logging.basicConfig(level=conf.logging.LEVEL, handlers=[handler])

    for logger_name in logging.root.manager.loggerDict:
        logger = logging.getLogger(logger_name)
        logger.handlers = [handler]
        logger.propagate = False  # Prevent log propagation to avoid duplicates


def configure() -> None:
    _configure_structlog_logging()
    _configure_loggers()


def get_logger(name: str = conf.app.SLUG, **context_kwargs: dict[str, str]) -> Logger:
    return Logger(structlog.get_logger(name, **context_kwargs))
