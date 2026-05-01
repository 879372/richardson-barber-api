import logging
from django.utils import timezone
from .models import Notification

logger = logging.getLogger(__name__)

class WhatsAppService:
    @staticmethod
    def send_message(appointment, message_type, content):
        """
        Mock method to send WhatsApp message.
        In a real scenario, this would call Evolution API, WPPConnect, or Meta Cloud API.
        """
        # 1. Create notification log
        notification = Notification.objects.create(
            appointment=appointment,
            type=message_type,
            message=content,
            status='pending'
        )

        # 2. Mock sending process
        try:
            # Here you would do: requests.post(API_URL, data=...)
            logger.info(f"MOCK WHATSAPP SEND: To {appointment.client.phone if appointment.client else 'N/A'} - Msg: {content}")
            
            # Simulate success
            notification.status = 'sent'
            notification.sent_at = timezone.now()
            notification.save()
            return True
        except Exception as e:
            logger.error(f"WHATSAPP SEND FAILED: {str(e)}")
            notification.status = 'failed'
            notification.save()
            return False

    @classmethod
    def send_confirmation(cls, appointment):
        from django.utils import timezone
        local_dt = timezone.localtime(appointment.date_time)
        msg = f"Olá {appointment.client.first_name if appointment.client else 'Cliente'}, seu agendamento para {appointment.service.name} em {local_dt.strftime('%d/%m às %H:%M')} foi confirmado! 💈"
        return cls.send_message(appointment, 'confirmation', msg)

    @classmethod
    def send_cancellation(cls, appointment):
        from django.utils import timezone
        local_dt = timezone.localtime(appointment.date_time)
        msg = f"Olá, seu agendamento para {appointment.service.name} em {local_dt.strftime('%d/%m às %H:%M')} foi cancelado. 😔"
        return cls.send_message(appointment, 'cancellation', msg)

    @classmethod
    def send_post_visit(cls, appointment):
        msg = f"Obrigado pela visita, {appointment.client.first_name if appointment.client else 'Cliente'}! Esperamos que tenha gostado do serviço {appointment.service.name}. Quando quiser agendar novamente, use nosso portal: https://richardsonbarber.app/agendar"
        return cls.send_message(appointment, 'confirmation', msg) # Using confirmation type or new post_visit type
