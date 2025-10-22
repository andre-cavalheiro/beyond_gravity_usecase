from collections.abc import AsyncGenerator
from typing import Annotated, TYPE_CHECKING

from fastapi import Depends

from fury_api.lib.security import get_current_user
from fury_api.lib.factories import UnitOfWork, UnitOfWorkFactory
from fury_api.lib.security import get_current_organization_id

if TYPE_CHECKING:
    from fury_api.domain.users.models import User


__all__ = ["get_uow_any_tenant", "get_uow_tenant", "get_uow_tenant_ro", "get_uow_query_ro", "get_uow", "get_uow_ro"]


async def get_uow_any_tenant() -> AsyncGenerator[UnitOfWork, None]:
    """Get a new unit of work."""
    async with UnitOfWorkFactory.get_uow() as uow:
        yield uow


async def get_uow_tenant(
    uow: Annotated[UnitOfWork, Depends(get_uow_any_tenant)],
    organization_id: Annotated[int, Depends(get_current_organization_id)],
) -> AsyncGenerator[UnitOfWork, None]:
    """Get a new unit of work with access to current tenant."""
    async with uow.with_organization(organization_id=organization_id, read_only=False, query_user=False):
        yield uow


async def get_uow_tenant_ro(
    uow: Annotated[UnitOfWork, Depends(get_uow_any_tenant)],
    organization_id: Annotated[int, Depends(get_current_organization_id)],
) -> AsyncGenerator[UnitOfWork, None]:
    """Get a new unit of work with access to current tenant in read only mode."""
    async with uow.with_organization(organization_id=organization_id, read_only=True, query_user=False):
        yield uow


async def get_uow_query_ro(
    uow: Annotated[UnitOfWork, Depends(get_uow_any_tenant)],
    organization_id: Annotated[int, Depends(get_current_organization_id)],
) -> AsyncGenerator[UnitOfWork, None]:
    """Get a new unit of work with access to current tenant in read only access mode to query model readable tables."""
    async with uow.with_organization(organization_id=organization_id, read_only=True, query_user=True):
        yield uow


async def get_uow(
    uow: Annotated[UnitOfWork, Depends(get_uow_tenant)], current_user: Annotated["User", Depends(get_current_user)]
) -> AsyncGenerator[UnitOfWork, None]:
    """Get a new unit of work with access to current tenant and block demo users."""
    yield uow


async def get_uow_ro(uow: Annotated[UnitOfWork, Depends(get_uow_tenant_ro)]) -> AsyncGenerator[UnitOfWork, None]:
    """Get a new unit of work with access to current tenant in read-only mode."""
    yield uow
