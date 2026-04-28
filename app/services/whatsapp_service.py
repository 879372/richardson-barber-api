import logging
from datetime import datetime, timezone
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.whatsapp import WhatsAppLog, WhatsAppTemplate, WhatsAppMessageType, WhatsAppStatus
from app.models.schedule import Schedule
from app.models.client import Client

logger = logging.getLogger(__name__)

DEFAULT_TEMPLATES = {
    WhatsAppMessageType.BOOKING_CONFIRMATION: (
        "Olá, {name}! Seu agendamento na {barbershop} foi confirmado para {date} às {time}. Te esperamos! 💈"
    ),
    WhatsAppMessageType.REMINDER_24H: (
        "Oi, {name}! Lembrando do seu agendamento amanhã, {date} às {time}. Qualquer dúvida, estamos à disposição. 😊"
    ),
    WhatsAppMessageType.REMINDER_1H: (
        "Oi, {name}! Daqui a 1 hora é o seu horário na {barbershop}. Até já! ✂️"
    ),
    WhatsAppMessageType.POST_SERVICE: (
        "Obrigado pela visita, {name}! Esperamos ter atendido bem. Quando quiser agendar novamente: {booking_url} 💈"
    ),
}


class WhatsAppService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _get_template(self, msg_type: WhatsAppMessageType) -> str:
        result = await self.db.execute(
            select(WhatsAppTemplate).where(
                WhatsAppTemplate.message_type == msg_type,
                WhatsAppTemplate.is_active == True,
            )
        )
        template = result.scalar_one_or_none()
        if template:
            return template.template_text
        return DEFAULT_TEMPLATES[msg_type]

    async def _get_schedule_with_client(self, schedule_id: UUID):
        result = await self.db.execute(
            select(Schedule).where(Schedule.id == schedule_id)
        )
        schedule = result.scalar_one_or_none()
        if not schedule:
            return None, None
        client_result = await self.db.execute(
            select(Client).where(Client.id == schedule.client_id)
        )
        client = client_result.scalar_one_or_none()
        return schedule, client

    def _format_template(self, template: str, schedule: Schedule, client: Client) -> str:
        local_dt = schedule.scheduled_at
        return template.format(
            name=client.name,
            barbershop=settings.BARBERSHOP_NAME,
            date=local_dt.strftime("%d/%m/%Y"),
            time=local_dt.strftime("%H:%M"),
            booking_url=settings.BARBERSHOP_BOOKING_URL,
        )

    async def _send_message(self, phone: str, message: str) -> bool:
        """Send message via configured WhatsApp provider."""
        try:
            if settings.WHATSAPP_PROVIDER == "evolution":
                async with httpx.AsyncClient(timeout=10) as client:
                    resp = await client.post(
                        f"{settings.WHATSAPP_API_URL}/message/sendText/{settings.WHATSAPP_INSTANCE}",
                        headers={"apikey": settings.WHATSAPP_API_KEY},
                        json={"number": phone, "text": message},
                    )
                    return resp.status_code == 201
            elif settings.WHATSAPP_PROVIDER == "zapi":
                async with httpx.AsyncClient(timeout=10) as client:
                    resp = await client.post(
                        f"{settings.WHATSAPP_API_URL}/send-text",
                        headers={"Client-Token": settings.WHATSAPP_API_KEY},
                        json={"phone": phone, "message": message},
                    )
                    return resp.status_code == 200
            else:
                logger.warning("WhatsApp provider not configured")
                return False
        except Exception as e:
            logger.error(f"WhatsApp send error: {e}")
            return False

    async def _dispatch(
        self,
        schedule_id: UUID,
        msg_type: WhatsAppMessageType,
        schedule: Schedule,
        client: Client,
    ) -> None:
        template = await self._get_template(msg_type)
        body = self._format_template(template, schedule, client)

        success = await self._send_message(client.phone, body)

        log = WhatsAppLog(
            schedule_id=schedule_id,
            recipient_phone=client.phone,
            message_type=msg_type,
            message_body=body,
            status=WhatsAppStatus.SENT if success else WhatsAppStatus.FAILED,
            sent_at=datetime.now(timezone.utc) if success else None,
        )
        self.db.add(log)
        await self.db.flush()

    async def send_booking_confirmation(self, schedule_id: UUID) -> None:
        schedule, client = await self._get_schedule_with_client(schedule_id)
        if schedule and client:
            await self._dispatch(schedule_id, WhatsAppMessageType.BOOKING_CONFIRMATION, schedule, client)

    async def send_reminder_24h(self, schedule_id: UUID) -> None:
        schedule, client = await self._get_schedule_with_client(schedule_id)
        if schedule and client:
            await self._dispatch(schedule_id, WhatsAppMessageType.REMINDER_24H, schedule, client)

    async def send_reminder_1h(self, schedule_id: UUID) -> None:
        schedule, client = await self._get_schedule_with_client(schedule_id)
        if schedule and client:
            await self._dispatch(schedule_id, WhatsAppMessageType.REMINDER_1H, schedule, client)

    async def send_post_service(self, schedule_id: UUID) -> None:
        schedule, client = await self._get_schedule_with_client(schedule_id)
        if schedule and client:
            await self._dispatch(schedule_id, WhatsAppMessageType.POST_SERVICE, schedule, client)
