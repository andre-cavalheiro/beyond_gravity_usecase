from fury_api.lib.unit_of_work import UnitOfWork
from fury_api.lib.db import async_session, async_session_ro
from fury_api.lib.settings import config

__all__ = ["UnitOfWorkFactory", "UnitOfWork"]


class UnitOfWorkFactory:
    @staticmethod
    def get_uow(*, organization_id: int | None = None, read_only: bool = False, query_user: bool = False) -> UnitOfWork:
        """Create a new UnitOfWork instance.

        Args:
            organization_id: Optional organization ID for tenant context
            read_only: Whether the unit of work should be read-only
            query_user: Whether to use query user role

        Returns:
            A new UnitOfWork instance
        """
        session_factory = async_session_ro if read_only else async_session
        if session_factory.kw.get("info", {}).get("read_only"):
            read_only = True

        return UnitOfWork(
            session_factory=session_factory,
            autocommit=config.api.SERVICES_AUTOCOMMIT,
            organization_id=organization_id,
            read_only=read_only,
            query_user=query_user,
        )
