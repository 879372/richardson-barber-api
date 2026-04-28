from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schedule import Schedule, Payment, ScheduleStatus
from app.models.client import Client
from app.repositories.schedule_repository import ScheduleRepository
from app.repositories.user_repository import UserRepository
from app.schemas.booking import ScheduleCreate, ScheduleUpdate, CompleteScheduleRequest, ScheduleOut
from app.services.whatsapp_service import WhatsAppService


class ScheduleService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ScheduleRepository(db)
        self.user_repo = UserRepository(db)

    async def create(self, data: ScheduleCreate, created_by_id: UUID | None = None) -> Schedule:
        from sqlalchemy import select
        from app.models.service import Service

        # Fetch service to get duration and price
        svc_result = await self.db.execute(
            select(Service).where(Service.id == data.service_id, Service.is_active == True)
        )
        service = svc_result.scalar_one_or_none()
        if not service:
            raise HTTPException(status_code=404, detail="Serviço não encontrado ou inativo")

        # Validate barber exists
        barber = await self.user_repo.get_by_id(data.barber_id)
        if not barber:
            raise HTTPException(status_code=404, detail="Profissional não encontrado")

        start = data.scheduled_at
        end = start + timedelta(minutes=service.duration_minutes)

        # Check for conflicts
        conflict = await self.repo.check_conflict(data.barber_id, start, end)
        if conflict:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Horário já ocupado para este profissional",
            )

        schedule = Schedule(
            client_id=data.client_id,
            barber_id=data.barber_id,
            service_id=data.service_id,
            scheduled_at=start,
            ends_at=end,
            total_price=float(service.price),
            notes=data.notes,
            status=ScheduleStatus.PENDING,
        )
        created = await self.repo.create(schedule)

        # Send WhatsApp booking confirmation
        try:
            wa = WhatsAppService(self.db)
            await wa.send_booking_confirmation(created.id)
        except Exception:
            pass  # WhatsApp failure must not block booking

        return created

    async def complete(self, schedule_id: UUID, data: CompleteScheduleRequest) -> Schedule:
        schedule = await self.repo.get_by_id_with_relations(schedule_id)
        if not schedule:
            raise HTTPException(status_code=404, detail="Agendamento não encontrado")

        if schedule.status != ScheduleStatus.CONFIRMED:
            raise HTTPException(
                status_code=400,
                detail="Apenas agendamentos confirmados podem ser concluídos",
            )

        total_paid = sum(p.amount for p in data.payments)
        if round(total_paid, 2) != round(float(schedule.total_price), 2):
            raise HTTPException(
                status_code=400,
                detail=f"Soma dos pagamentos (R$ {total_paid:.2f}) diverge do valor do serviço (R$ {float(schedule.total_price):.2f})",
            )

        # Persist payments
        for p in data.payments:
            payment = Payment(
                schedule_id=schedule_id,
                method=p.method,
                amount=p.amount,
            )
            self.db.add(payment)

        schedule.status = ScheduleStatus.COMPLETED
        await self.db.flush()

        # Update client total_spent
        from sqlalchemy import select
        from app.models.client import Client
        client_result = await self.db.execute(
            select(Client).where(Client.id == schedule.client_id)
        )
        client = client_result.scalar_one_or_none()
        if client:
            client.total_spent = float(client.total_spent) + float(schedule.total_price)

        # Send post-service WhatsApp
        try:
            wa = WhatsAppService(self.db)
            await wa.send_post_service(schedule_id)
        except Exception:
            pass

        return schedule

    async def update_status(self, schedule_id: UUID, new_status: ScheduleStatus) -> Schedule:
        schedule = await self.repo.get_by_id(schedule_id)
        if not schedule:
            raise HTTPException(status_code=404, detail="Agendamento não encontrado")
        schedule.status = new_status
        await self.db.flush()
        return schedule
