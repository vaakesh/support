from abc import ABC, abstractmethod
from typing import Generic, TypeVar

T = TypeVar("T")


class AbstractRepository(ABC, Generic[T]):
    @abstractmethod
    async def get_by_id(self, entity_id: int) -> T | None: ...

    @abstractmethod
    def add(self, entity: T) -> None: ...

    @abstractmethod
    async def delete(self, entity: T) -> None: ...

    @abstractmethod
    async def refresh(self, entity: T) -> None: ...
