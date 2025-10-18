from typing import Any, TypeVar
from sqlalchemy import select
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from fury_api.domain.organizations.models import Organization
from fury_api.lib.repository import GenericSqlExtendedRepository


T = TypeVar("T", bound=SQLModel)

__all__ = ["OrganizationRepository"]


class OrganizationRepository(GenericSqlExtendedRepository[Organization]):
    def __init__(self) -> None:
        super().__init__(model_cls=Organization)
