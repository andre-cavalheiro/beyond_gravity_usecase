from sqlalchemy import select
from sqlmodel.ext.asyncio.session import AsyncSession

from fury_api.domain.users.models import User
from fury_api.lib.repository import GenericSqlExtendedRepository

__all__ = ["UserRepository"]


class UserRepository(GenericSqlExtendedRepository[User]):
    def __init__(self) -> None:
        super().__init__(model_cls=User)

    async def get_by_email(self, session: AsyncSession, email: str) -> User | None:
        q = select(self._model_cls).where(self._model_cls.email == email)
        result = await session.exec(q)
        return result.scalar_one_or_none()
