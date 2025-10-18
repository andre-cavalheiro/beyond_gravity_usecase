from __future__ import annotations

from abc import ABC, abstractmethod

__all__ = ["AsyncAbstractUnitOfWork"]


class AsyncAbstractUnitOfWork(ABC):
    async def __aenter__(self) -> AsyncAbstractUnitOfWork:
        """This method is called when entering the context manager."""
        return self

    async def __aexit__(self, *args: tuple, **kwargs: dict) -> None:
        """This method is called when exiting the context manager."""
        await self.rollback()

    @abstractmethod
    async def commit(self) -> None:
        raise NotImplementedError

    @abstractmethod
    async def rollback(self) -> None:
        raise NotImplementedError
