from typing import TYPE_CHECKING
from fury_api.lib.settings import config

from fury_api.lib.factories.service_factory import ServiceFactory, ServiceType
from fury_api.lib.unit_of_work import UnitOfWork

from fury_api.domain.organizations.models import Organization
from fury_api.domain.users.models import User

from fury_api.lib.logging import get_logger

if TYPE_CHECKING:
    pass

__all__ = [
    "get_organization",
    "create_organization",
    "delete_organization",
    "update_organization",
]

_logger = get_logger(__name__)

async def get_organizations(uow: UnitOfWork) -> list[Organization] | None:
    return await uow.organizations.list(uow.session)


async def get_organization(uow: UnitOfWork, organization_id: int) -> Organization | None:
    return await uow.organizations.get_by_id(uow.session, organization_id)


async def create_organization(
    uow: UnitOfWork,
    organization: Organization,
    current_user: User,
) -> Organization:
    async with uow:
        await uow.organizations.add(uow.session, organization)

        async with uow.with_organization(organization_id=organization.id):
            users_service = ServiceFactory.create_service(ServiceType.USERS, uow)
            # Create primary user for organization
            current_user.organization_id = organization.id
            if not current_user.name:
                current_user.name = current_user.email
            await users_service.create_user(current_user)

    return organization


async def delete_organization(
    uow: UnitOfWork,
    organization_id: int,
) -> Organization | None:
    async with uow:
        # TODO: Organization delete is currently broken due to foreign key constraints
        deleted_organization = await uow.organizations.delete(uow.session, organization_id)

    return deleted_organization


async def update_organization(uow: UnitOfWork, organization_id: int, organization: Organization) -> Organization | None:
    async with uow:
        existing_organization = await uow.organizations.get_by_id(uow.session, organization_id)
        if existing_organization is None:
            return None
        if organization.id != existing_organization.id:
            raise
        existing_organization.update(organization)
        await uow.organizations.update(uow.session, existing_organization)

        return existing_organization
