from fastapi import Depends
from fastapi.routing import APIRouter, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import InterfaceError, OperationalError

from fury_api.domain import paths
from fury_api.lib.dependencies.unit_of_work import get_uow_any_tenant
from fury_api.lib.unit_of_work import UnitOfWork
from fury_api.lib.logging import get_logger

_logger = get_logger(__name__)


health_router = APIRouter()


@health_router.get(
    paths.HEALTH_CHECK,
    summary="Perform a Health Check",
    response_description="Return HTTP Status Code 200 (OK) if the service is up and running",
)
async def healthcheck(
    uow: UnitOfWork = Depends(get_uow_any_tenant),
    status_code: int = 503,
    detail: str = "Service Unavailable",
) -> dict:
    try:
        # Perform a simple query to check if the database is up
        result = await uow.session.exec(select(1))
        db_status = "ok" if result.scalar() == 1 else "not ok"
    except (InterfaceError, OperationalError, TimeoutError, OSError) as err:
        raise HTTPException(status_code=status_code, detail=detail) from err

    return {"status": "ok", "db_status": db_status}


@health_router.get(
    paths.HEALTH_CHECK_VELINI,
    summary="Perform a Health Check by Velini",
    response_description="Return HTTP Status Code 500 (NOT OK) if the service is up and running",
)
async def healthcheck_velini(
    uow: UnitOfWork = Depends(get_uow_any_tenant),
    status_code: int = 503,
    detail: str = "Service Unavailable",
) -> dict:
    return {"hello velini": "world"}
