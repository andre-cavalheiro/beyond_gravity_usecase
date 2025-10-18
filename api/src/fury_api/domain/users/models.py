from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import BigInteger, String
from sqlmodel import TIMESTAMP, Field, Relationship, func

from fury_api.lib.db.base import BaseSQLModel, NoneNullable
from fury_api.domain.organizations.models import Organization


class UserStatus(int, Enum):
    NON_EXISTENT = 1
    ACTIVE = 1
    INACTIVE = 2
    DELETED = 3


class UserBase(BaseSQLModel):
    name: str = Field(min_length=1)
    email: str = Field(min_length=1, unique=True)


class User(UserBase, table=True):
    __tablename__: str = "user"
    __id_attr__ = "id"

    id: int = Field(primary_key=True, sa_type=BigInteger, sa_column_kwargs={"autoincrement": True})
    firebase_id: str = Field(None, sa_type=String)
    organization_id: int | None = Field(None, foreign_key="organization.id", nullable=False)

    status: int = Field(UserStatus.ACTIVE, sa_column_kwargs={"server_default": "1"})
    is_system: bool = Field(False, sa_column_kwargs={"server_default": "false"})
    active_token_id: str | None = Field(None)

    last_login: datetime | None = Field(
        None, sa_type=TIMESTAMP(timezone=True)
    )  # FIXME: This isn't actually being populated anywhere.
    date_joined: datetime = Field(sa_type=TIMESTAMP(timezone=True), sa_column_kwargs={"server_default": func.now()})

    # Relationships
    organization: "Organization" = Relationship(back_populates="users", sa_relationship_kwargs={"lazy": "joined"})


class UserRead(UserBase):
    id: int = Field()
    last_login: datetime | NoneNullable
    date_joined: datetime
    status: UserStatus


class UserReadProvisional(UserBase):
    id: Optional[int] = Field(None)
    organization_id: Optional[int] = Field(None)
    status: Optional[int] = Field(UserStatus.NON_EXISTENT)
    last_login: Optional[datetime] = None
    date_joined: Optional[datetime] = None
