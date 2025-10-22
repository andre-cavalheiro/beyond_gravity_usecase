import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Security, Request, status

from fury_api.domain import paths
from fury_api.lib.dependencies import (
    get_service,
    get_uow,
    get_uow_any_tenant,
    get_uow_ro,
)
from fury_api.lib.settings import config
from fury_api.lib.factories.service_factory import ServiceType
from fury_api.domain.organizations import exceptions, services
from fury_api.domain.users.models import User
from fury_api.domain.organizations.models import (
    Organization,
    OrganizationCreate,
    OrganizationRead,
)
from fury_api.lib.security import get_current_user, get_current_user_new_organization
from fury_api.lib.unit_of_work import UnitOfWork
from fury_api.domain.users.services import UsersService

user_auth_router = APIRouter(dependencies=[Security(get_current_user)])
user_auth_new_organization_router = APIRouter(dependencies=[Depends(get_current_user_new_organization)])

@user_auth_router.get(paths.ORGANIZATIONS_SELF, response_model=OrganizationRead)
async def get_organization_me(
    uow: Annotated[UnitOfWork, Depends(get_uow_ro)], current_user: Annotated[User, Depends(get_current_user)]
) -> Organization:
    return await services.get_organization(uow, current_user.organization_id)


@user_auth_router.delete(paths.ORGANIZATIONS_SELF, response_model=OrganizationRead)
async def delete_organization_me(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Organization:
    return await services.delete_organization(uow, current_user.organization_id)


@user_auth_new_organization_router.post(
    paths.ORGANIZATIONS,
    response_model=OrganizationRead,
    response_model_exclude_unset=True,
    status_code=status.HTTP_201_CREATED,
)
async def create_organization(
    organization: OrganizationCreate,
    uow: Annotated[UnitOfWork, Depends(get_uow_any_tenant)],
    current_user: Annotated[User, Depends(get_current_user_new_organization)],
    users_service: Annotated[
        UsersService,
        Depends(
            get_service(
                ServiceType.USERS,
                has_system_access=True,
                uow=Depends(get_uow_any_tenant),
                auth_user=Depends(get_current_user_new_organization),
            )
        ),
    ],
) -> Organization:
    existing_user = await users_service.get_user_by_email(email=current_user.email)
    if existing_user is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User with that email already exists")

    organization_obj = Organization.parse_obj(organization)
    try:
        new_organization = await services.create_organization(uow, organization_obj, current_user=current_user)
    except exceptions.OrganizationsError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    return new_organization

organization_router = APIRouter()
organization_router.include_router(user_auth_router)
organization_router.include_router(user_auth_new_organization_router)
