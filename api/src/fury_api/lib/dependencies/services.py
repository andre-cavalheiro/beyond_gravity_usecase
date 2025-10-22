from collections.abc import Callable
from typing import Annotated, Any, TYPE_CHECKING

from fastapi import Depends

from fury_api.lib.dependencies.unit_of_work import get_uow, get_uow_ro
from fury_api.lib.factories.service_factory import ServiceFactory, ServiceType
from fury_api.lib.service import SqlService
from fury_api.lib.unit_of_work import UnitOfWork
from fury_api.lib.security import get_current_user

if TYPE_CHECKING:
    from fury_api.domain.users.models import User


def get_service(
    service_type: ServiceType,
    read_only: bool = False,
    *,
    uow: UnitOfWork | None = None,
    auth_user: "User | None" = None,
    **kwargs: Any,
) -> Callable[..., SqlService]:
    def dependency(
        uow: Annotated[UnitOfWork, uow or Depends(get_uow if not read_only else get_uow_ro)],
        auth_user: Annotated["User", auth_user or Depends(get_current_user)],
    ) -> SqlService:
        return ServiceFactory.create_service(
            service_type,
            uow,
            auth_user=auth_user,
            **kwargs,
        )

    return dependency



def get_service_admin(
    service_type: ServiceType,
    read_only: bool = False,
    *,
    uow: UnitOfWork | None = None,
    **kwargs: Any,
) -> Callable[..., SqlService]:
    def dependency(
        uow: Annotated[UnitOfWork, uow or Depends(get_uow if not read_only else get_uow_ro)],
    ) -> SqlService:
        return ServiceFactory.create_service(
            service_type,
            uow,
            **kwargs,
        )

    return dependency
