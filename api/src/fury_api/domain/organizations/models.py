from enum import StrEnum
from typing import Optional

from fury_api.lib.db.base import BaseSQLModel, BigIntIDModel
from sqlalchemy import BigInteger
from sqlmodel import Field, Relationship

__all__ = [
    "Organization",
    "OrganizationCreate",
    "OrganizationRead",
]


class OrganizationBase(BaseSQLModel):
    name: str = ""


class Organization(OrganizationBase, BigIntIDModel, table=True):
    __tablename__: str = "organization"
    __id_attr__ = "id"

    id: int = Field(primary_key=True, sa_type=BigInteger, sa_column_kwargs={"autoincrement": True})

    users: list["User"] = Relationship(  # noqa (otherwise, circular dependency for User)
        back_populates="organization", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )


class OrganizationRead(Organization):
    pass


class OrganizationCreate(OrganizationBase):
    pass
