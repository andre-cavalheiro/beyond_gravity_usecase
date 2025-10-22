from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Security, status

from fury_api.domain import paths
from fury_api.lib.dependencies import ServiceType, get_service, get_uow_any_tenant, get_uow_tenant_ro
from fury_api.lib.security import get_current_user, get_user_from_token
from fury_api.domain.users.models import (
    User,
    UserReadProvisional,
    UserRead,
)
from fury_api.domain.users.services import UsersService

# Standard router that ensures the user exists in the database
user_auth_router = APIRouter(dependencies=[Security(get_current_user)])

# Router for cases where some fields are optional, so user existence in the database is not mandatory
user_auth_router_optional_fields = APIRouter(dependencies=[Security(get_user_from_token)])


@user_auth_router_optional_fields.get(paths.USERS_SELF, response_model=UserReadProvisional)
async def get_self_user(
    current_user: Annotated[User, Depends(get_user_from_token)],
    users_service: Annotated[
        UsersService,
        Depends(
            get_service(
                ServiceType.USERS,
                has_system_access=True,
                uow=Depends(get_uow_any_tenant),
                auth_user=Depends(get_user_from_token),
            )
        ),
    ],
) -> UserReadProvisional:
    existing_user = await users_service.get_user_by_email(current_user.email)
    return existing_user if existing_user else UserReadProvisional(name=current_user.name, email=current_user.email)


@user_auth_router.get(paths.USERS, response_model=list[UserRead])
async def get_users(
    user_service: Annotated[
        UsersService,
        Depends(
            get_service(
                ServiceType.USERS,
                read_only=True,
                uow=Depends(get_uow_tenant_ro),
            )
        ),
    ],
) -> list[UserRead]:
    return [user async for user in user_service.get_users()]


@user_auth_router.delete(paths.USERS_ID, status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    id_: int,
    user_service: Annotated[UsersService, Depends(get_service(ServiceType.USERS))],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    if id_ == current_user.user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You can't delete yourself")
    user = await user_service.get_user_by_id(id_)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user_service.has_system_access = user.is_system
    await user_service.delete_user(user)


user_router = APIRouter()
user_router.include_router(user_auth_router)
user_router.include_router(user_auth_router_optional_fields)
