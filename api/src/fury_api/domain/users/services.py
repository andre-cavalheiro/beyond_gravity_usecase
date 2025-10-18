import uuid
from collections.abc import Generator
from typing import TYPE_CHECKING, Any

from fury_api.core.service import SqlService, with_uow
from fury_api.core.unit_of_work import UnitOfWork
from fury_api.domain.users import exceptions
from fury_api.domain.users.models import User, UserStatus
from fury_api.domain.users.utils import generate_system_user_name
from fury_api.lib.pagination import CursorPage
from fury_api.core import security

if TYPE_CHECKING:
    pass

__all__ = ["UsersService"]


class UsersService(SqlService[User]):
    def __init__(
        self,
        uow: UnitOfWork,
        *,
        auth_user: User | None = None,
        has_system_access: bool = False,
        **kwargs,
    ):
        super().__init__(User, uow, auth_user=auth_user, **kwargs)
        self.has_system_access = has_system_access

    @with_uow
    async def get_user_by_id(self, id_: int) -> User | None:
        user = await self.repository.get_by_id(self.session, id_)
        if user is None or (not self.has_system_access and user.is_system):
            return None
        return user

    @with_uow
    async def get_user_by_email(self, email: str) -> User | None:
        user = await self.repository.get_by_email(self.session, email)
        if user is None or (not self.has_system_access and user.is_system):
            return None
        return user

    @property
    def _default_list_filters(self) -> dict[str, Any]:
        return {} if self.has_system_access else {"is_system": False}

    @with_uow
    async def get_users(self) -> Generator[User, None, None]:
        for user in await self.repository.list(self.session, filters=self._default_list_filters):
            yield user

    @with_uow
    async def get_users_paginated(self) -> CursorPage[User]:
        return await self.repository.list_with_pagination(self.session, filters=self._default_list_filters)

    @with_uow
    async def create_user(self, user: User) -> User:
        if not self.has_system_access and user.is_system:
            raise exceptions.UserNoSystemAccessError()
        if self.auth_user is not None:
            user.organization_id = self.auth_user.organization_id

        legacy_user: User = await self.repository.add(self.session, user)

        return legacy_user

    @with_uow
    async def delete_user(self, user: User) -> User | None:
        if user.is_system and not self.has_system_access:
            return None

        user = await self.repository.delete(self.session, user.id)
        # TODO: Delete from firebase too

        return user

    @with_uow
    async def is_system_user(self, id_: int) -> bool:
        with self.override_attributes(has_system_access=True):
            user = await self.get_user_by_id(id_)
            return user.is_system if user else False

    @with_uow
    async def create_system_user(self, organization_id: int) -> None:
        if not self.has_system_access:
            raise exceptions.UserNoSystemAccessError()

        rand_name = generate_system_user_name()
        user = User(
            name=rand_name,
            email=f"bot-{rand_name}@fury.api",
            organization_id=organization_id,
            status=UserStatus.ACTIVE,
            is_system=True,
        )
        user = await self.create_user(user)
        return user

    @with_uow
    async def create_long_lived_token_for_user(self, user: User) -> str:
        token_id = str(uuid.uuid4())
        token = security.create_long_lived_token(token_id, user.name, user.email)
        user.active_token_id = token_id
        _ = await self.repository.update(self.session, user)
        return token
