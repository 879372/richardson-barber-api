from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.models.schedule import Schedule, ScheduleStatus
from app.models.user import User, UserRole
from app.schemas.booking import (
    ScheduleCreate,
    ScheduleUpdate,
    ScheduleOut,
    CompleteScheduleRequest,
)
from app.services.schedule_service import ScheduleService
from app.repositories.schedule_repository import ScheduleRepository

router = APIRouter(prefix="/schedules", tags=["schedules"])


@router.post("/", response_model=ScheduleOut, status_code=status.HTTP_201_CREATED)
async def create_schedule(
    data: ScheduleCreate,
    db: AsyncSession = Depends(get_db),
):
    """Public endpoint — no auth required for client booking."""
    svc = ScheduleService(db)
    return await svc.create(data)


@router.get("/", response_model=list[ScheduleOut])
async def list_schedules(
    barber_id: UUID | None = Query(None),
    date: str | None = Query(None, description="YYYY-MM-DD"),
    status: ScheduleStatus | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Schedule)

    # Barbers only see their own schedules
    if current_user.role == UserRole.BARBER:
        query = query.where(Schedule.barber_id == current_user.id)
    elif barber_id:
        query = query.where(Schedule.barber_id == barber_id)

    if date:
        from datetime import date as date_type
        parsed = datetime.strptime(date, "%Y-%m-%d")
        day_start = parsed.replace(hour=0, minute=0, second=0, tzinfo=timezone.utc)
        day_end = parsed.replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
        query = query.where(Schedule.scheduled_at >= day_start, Schedule.scheduled_at <= day_end)

    if status:
        query = query.where(Schedule.status == status)

    result = await db.execute(query.order_by(Schedule.scheduled_at))
    return list(result.scalars().all())


@router.get("/summary", response_model=dict)
async def daily_summary(
    barber_id: UUID | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    target_id = barber_id if barber_id and current_user.role != UserRole.BARBER else current_user.id
    repo = ScheduleRepository(db)
    return await repo.get_daily_summary(target_id, datetime.now(timezone.utc))


@router.get("/{schedule_id}", response_model=ScheduleOut)
async def get_schedule(
    schedule_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = ScheduleRepository(db)
    schedule = await repo.get_by_id_with_relations(schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado")
    if current_user.role == UserRole.BARBER and schedule.barber_id != current_user.id:
        raise HTTPException(status_code=403, detail="Acesso negado")
    return schedule


@router.patch("/{schedule_id}/status", response_model=ScheduleOut)
async def update_status(
    schedule_id: UUID,
    data: ScheduleUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = ScheduleService(db)
    if data.status:
        return await svc.update_status(schedule_id, data.status)
    raise HTTPException(status_code=400, detail="Informe o novo status")


@router.post("/{schedule_id}/complete", response_model=ScheduleOut)
async def complete_schedule(
    schedule_id: UUID,
    data: CompleteScheduleRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = ScheduleService(db)
    return await svc.complete(schedule_id, data)


@router.get("/available-slots", response_model=list[str])
async def available_slots(
    barber_id: UUID = Query(...),
    date: str = Query(..., description="YYYY-MM-DD"),
    service_id: UUID = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Return available time slots for a barber on a given date. Public endpoint."""
    from sqlalchemy import select
    from app.models.service import Service
    from app.models.availability import Availability

    parsed = datetime.strptime(date, "%Y-%m-%d")
    week_day = parsed.weekday()

    # Get barber availability for this weekday
    avail_result = await db.execute(
        select(Availability).where(
            Availability.barber_id == barber_id,
            Availability.week_day == week_day,
            Availability.is_active == True,
        )
    )
    availability = avail_result.scalar_one_or_none()
    if not availability:
        return []

    # Get service duration
    svc_result = await db.execute(select(Service).where(Service.id == service_id))
    service = svc_result.scalar_one_or_none()
    if not service:
        return []

    # Get existing bookings for the day
    repo = ScheduleRepository(db)
    day_start = parsed.replace(hour=0, minute=0, second=0, tzinfo=timezone.utc)
    day_end = parsed.replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
    existing = await repo.get_by_barber_and_date(barber_id, day_start, day_end)

    booked_ranges = [(s.scheduled_at, s.ends_at) for s in existing]

    # Generate slots
    from datetime import timedelta
    start_h, start_m = map(int, availability.start_time.split(":"))
    end_h, end_m = map(int, availability.end_time.split(":"))
    slot_start = parsed.replace(hour=start_h, minute=start_m, second=0, tzinfo=timezone.utc)
    slot_end = parsed.replace(hour=end_h, minute=end_m, second=0, tzinfo=timezone.utc)
    duration = timedelta(minutes=service.duration_minutes)

    slots = []
    current = slot_start
    while current + duration <= slot_end:
        slot_finish = current + duration
        conflict = any(
            not (slot_finish <= b[0] or current >= b[1]) for b in booked_ranges
        )
        if not conflict:
            slots.append(current.strftime("%H:%M"))
        current += timedelta(minutes=30)

    return slots
