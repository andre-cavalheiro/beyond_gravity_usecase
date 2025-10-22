from __future__ import annotations

from typing import TYPE_CHECKING, cast

from fury_api.lib.exceptions import FuryValidationError

if TYPE_CHECKING:
    from fastapi import FastAPI


__all__ = ["create_app"]


def create_app() -> FastAPI:
    from fastapi import FastAPI

    from fury_api.lib.lifecycle import lifespan
    from fury_api.lib import settings

    # Create app
    app = FastAPI(
        # App
        debug=settings.config.app.DEBUG,
        lifespan=lifespan,
        # OpenAPI
        title=settings.config.openapi.TITLE,
        description=settings.config.openapi.DESCRIPTION,
        version=settings.config.openapi.VERSION,
        openapi_url=settings.config.openapi.SCHEMA_PATH,
        contact={"name": settings.config.openapi.CONTACT_NAME, "email": settings.config.openapi.CONTACT_EMAIL},
    )

    _configure_exception_handlers(app)
    _configure_middlewares(
        app,
        service_name=settings.config.app.NAME,
    )
    _configure_api(app)
    _openapi_schema_override(app)

    return app


def _configure_api(app: FastAPI) -> None:
    from fastapi_pagination import add_pagination

    from fury_api.domain.routes import create_router
    from fury_api.lib.responses import MsgSpecJSONResponse

    # API Pagination
    add_pagination(app)

    # Include API routes
    app.include_router(
        create_router(),
        default_response_class=MsgSpecJSONResponse,
        include_in_schema=True,
    )


def _configure_exception_handlers(app: FastAPI) -> None:
    from fastapi import Request, Response, status
    from fastapi.utils import is_body_allowed_for_status_code
    from jsonschema import SchemaError, ValidationError
    from starlette.exceptions import HTTPException as StarletteHTTPException

    from fury_api.lib.exceptions import (
        InternalServerError,
        FuryAPIError,
        FuryAPIHTTPError,
        FuryValidationError,
    )
    from fury_api.lib.logging import Logger
    from fury_api.lib.responses import MsgSpecJSONResponse

    def _get_logger(request: Request) -> Logger:
        return cast(Logger, request.state.logger)

    def _handle_internal_server_error(request: Request, exc: Exception) -> MsgSpecJSONResponse:
        if request.app.debug:
            raise exc
        _get_logger(request).error("Internal server error", exc_info=exc)
        return MsgSpecJSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"detail": "Internal server error"}
        )

    def _handle_jsonschema_schema_and_validation_error(
        request: Request, exc: ValidationError | SchemaError
    ) -> MsgSpecJSONResponse:
        error_type = getattr(exc, "validator", None)
        if error_type is None:
            error_type = "validation" if isinstance(exc, ValidationError) else "schema"
        error_type = f"{error_type}.error"

        return MsgSpecJSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": [{"loc": [], "msg": f"{exc.message}, location: {exc.json_path}", "type": error_type}]},
        )

    def _handle_fury_validation_error(request: Request, exc: FuryValidationError) -> MsgSpecJSONResponse:
        content = {"detail": exc.errors_details or exc.detail}
        if exc.msg:
            content["msg"] = exc.msg
        return MsgSpecJSONResponse(status_code=exc.status_code, content=content)

    def _handle_fury_api_http_error(request: Request, exc: FuryAPIHTTPError) -> MsgSpecJSONResponse:
        if isinstance(exc, InternalServerError):
            return _handle_internal_server_error(request, exc.exception)
        return MsgSpecJSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    def _handle_fury_api_error(request: Request, exc: FuryAPIError) -> MsgSpecJSONResponse:
        return _handle_internal_server_error(request, exc)

    # Fallback handlers if exceptions raised are not FuryAPIError
    def _handle_http_exception(request: Request, exc: StarletteHTTPException) -> MsgSpecJSONResponse:
        if exc.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR:
            return _handle_internal_server_error(request, exc)

        headers = getattr(exc, "headers", None)
        if not is_body_allowed_for_status_code(exc.status_code):
            return Response(status_code=exc.status_code, headers=headers)
        return MsgSpecJSONResponse({"detail": exc.detail}, status_code=exc.status_code, headers=headers)

    def _handle_any_exception(request: Request, exc: Exception) -> MsgSpecJSONResponse:
        return _handle_internal_server_error(request, exc)

    # Jsonschema exception handlers
    app.add_exception_handler(ValidationError, _handle_jsonschema_schema_and_validation_error)
    app.add_exception_handler(SchemaError, _handle_jsonschema_schema_and_validation_error)

    # Fury exception handlers
    app.add_exception_handler(FuryValidationError, _handle_fury_validation_error)
    app.add_exception_handler(FuryAPIHTTPError, _handle_fury_api_http_error)
    app.add_exception_handler(FuryAPIError, _handle_fury_api_error)

    # Fallback handlers if exceptions raised are not FuryAPIError
    app.add_exception_handler(StarletteHTTPException, _handle_http_exception)
    app.add_exception_handler(Exception, _handle_any_exception)


def _configure_middlewares(app: FastAPI, *, service_name: str) -> None:
    from fury_api.lib import compression, cors

    # Base middlewares
    app.add_middleware(**cors.middleware_config)
    app.add_middleware(**compression.middleware_config)


def _openapi_schema_override(app: FastAPI) -> None:
    _ = app.openapi()

    # Add bearerAuth to the securitySchemes section
    if "components" not in app.openapi_schema:
        app.openapi_schema["components"] = {}
    app.openapi_schema["components"]["securitySchemes"] = {"bearerAuth": {"type": "http", "scheme": "bearer"}}

    # Set the global security scheme
    app.openapi_schema["security"] = [{"bearerAuth": []}]
