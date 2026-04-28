from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, db: AsyncSession):
        super().__init__(User, db)

    async def get_by_email(self, email: str) -> User | None:
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_active_barbers(self) -> list[User]:
        from app.models.user import UserRole
        result = await self.db.execute(
            select(User).where(User.role == UserRole.BARBER, User.is_active == True)
        )
        return list(result.scalars().all())
