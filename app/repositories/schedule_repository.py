from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schedule import Schedule, ScheduleStatus, Payment
from app.repositories.base import BaseRepository


class ScheduleRepository(BaseRepository[Schedule]):
    def __init__(self, db: AsyncSession):
        super().__init__(Schedule, db)

    async def get_by_id_with_relations(self, id: UUID) -> Schedule | None:
        result = await self.db.execute(
            select(Schedule)
            .options(
                selectinload(Schedule.client),
                selectinload(Schedule.barber),
                selectinload(Schedule.service),
                selectinload(Schedule.payments),
            )
            .where(Schedule.id == id)
        )
        return result.scalar_one_or_none()

    async def get_by_barber_and_date(
        self, barber_id: UUID, date_start: datetime, date_end: datetime
    ) -> list[Schedule]:
        result = await self.db.execute(
            select(Schedule)
            .options(
                selectinload(Schedule.client),
                selectinload(Schedule.service),
                selectinload(Schedule.payments),
            )
            .where(
                and_(
                    Schedule.barber_id == barber_id,
                    Schedule.scheduled_at >= date_start,
                    Schedule.scheduled_at < date_end,
                    Schedule.status.notin_(
                        [ScheduleStatus.CANCELLED]
                    ),
                )
            )
            .order_by(Schedule.scheduled_at)
        )
        return list(result.scalars().all())

    async def check_conflict(
        self,
        barber_id: UUID,
        start: datetime,
        end: datetime,
        exclude_id: UUID | None = None,
    ) -> bool:
        query = select(Schedule).where(
            and_(
                Schedule.barber_id == barber_id,
                Schedule.status.notin_([ScheduleStatus.CANCELLED]),
                or_(
                    and_(Schedule.scheduled_at <= start, Schedule.ends_at > start),
                    and_(Schedule.scheduled_at < end, Schedule.ends_at >= end),
                    and_(Schedule.scheduled_at >= start, Schedule.ends_at <= end),
                ),
            )
        )
        if exclude_id:
            query = query.where(Schedule.id != exclude_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none() is not None

    async def get_daily_summary(self, barber_id: UUID, date: datetime) -> dict:
        day_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = date.replace(hour=23, minute=59, second=59, microsecond=999999)

        result = await self.db.execute(
            select(Schedule).where(
                and_(
                    Schedule.barber_id == barber_id,
                    Schedule.scheduled_at >= day_start,
                    Schedule.scheduled_at <= day_end,
                )
            )
        )
        schedules = list(result.scalars().all())

        total = len(schedules)
        completed = [s for s in schedules if s.status == ScheduleStatus.COMPLETED]
        revenue_realized = sum(float(s.total_price) for s in completed)
        revenue_forecast = sum(
            float(s.total_price)
            for s in schedules
            if s.status not in [ScheduleStatus.CANCELLED]
        )

        return {
            "total_appointments": total,
            "completed_appointments": len(completed),
            "revenue_realized": revenue_realized,
            "revenue_forecast": revenue_forecast,
        }
