"""
app/repositories/base_repository.py

Generic async CRUD repository — the foundation of the data access layer.

Design principles:
- Services never write SQLAlchemy queries directly; they call repository methods
- BaseRepository provides standard CRUD — subclasses only override custom queries
- All methods accept an AsyncSession (injected by the service via constructor)
- Type parameters ensure type safety: repository.get(id) returns the correct model type
"""

from __future__ import annotations

import uuid
from typing import Any, Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """
    Generic async CRUD repository.

    Type parameter ModelT is the SQLAlchemy ORM model class.

    Usage:
        class UserRepository(BaseRepository[User]):
            model = User

        # In a service:
        repo = UserRepository(db_session)
        user = await repo.get_by_id(user_id)
    """

    model: type[ModelT]  # Subclasses must declare this

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, record_id: uuid.UUID) -> ModelT | None:
        """Fetch a single record by primary key. Returns None if not found."""
        return await self.session.get(self.model, record_id)

    async def get_all(
        self,
        *,
        offset: int = 0,
        limit: int = 20,
        order_by: Any | None = None,
    ) -> list[ModelT]:
        """
        Fetch a paginated list of records.

        Args:
            offset:   Number of records to skip (for pagination).
            limit:    Maximum number of records to return.
            order_by: SQLAlchemy column expression to sort by.
        """
        stmt = select(self.model)
        if order_by is not None:
            stmt = stmt.order_by(order_by)
        stmt = stmt.offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count(self) -> int:
        """Return the total number of records in the table."""
        result = await self.session.execute(select(func.count()).select_from(self.model))
        return result.scalar_one()

    async def create(self, **kwargs: Any) -> ModelT:
        """
        Create and persist a new record.

        Args:
            **kwargs: Column values to set on the new record.

        Returns:
            The newly created, persisted model instance.
        """
        instance = self.model(**kwargs)
        self.session.add(instance)
        await self.session.flush()  # Flush to get DB-generated values (e.g., created_at)
        await self.session.refresh(instance)
        return instance

    async def update(self, instance: ModelT, **kwargs: Any) -> ModelT:
        """
        Update an existing record with the given field values.

        Args:
            instance: The ORM model instance to update.
            **kwargs: Field names and their new values.

        Returns:
            The updated model instance.
        """
        for field, value in kwargs.items():
            setattr(instance, field, value)
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def delete(self, instance: ModelT) -> None:
        """
        Delete a record from the database.

        Args:
            instance: The ORM model instance to delete.
        """
        await self.session.delete(instance)
        await self.session.flush()

    async def save(self, instance: ModelT) -> ModelT:
        """
        Add an instance to the session and flush.

        Useful when an instance was constructed externally and needs to be persisted.
        """
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance
