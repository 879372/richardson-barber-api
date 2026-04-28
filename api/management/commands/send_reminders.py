from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from api.models import Appointment, Notification
from api.whatsapp_service import WhatsAppService

class Command(BaseCommand):
    help = 'Envia lembretes de WhatsApp para agendamentos próximos (24h e 1h)'

    def handle(self, *args, **options):
        now = timezone.now()
        
        # 1. Reminders for 24h
        limit_24h = now + timedelta(hours=24)
        apps_24h = Appointment.objects.filter(
            status='confirmed',
            date_time__gt=now,
            date_time__lte=limit_24h
        ).exclude(notifications__type='reminder', notifications__message__contains='24h')

        for app in apps_24h:
            msg = f"Olá {app.client.first_name if app.client else 'Cliente'}, lembrete de que seu agendamento é amanhã às {app.date_time.strftime('%H:%M')}! 💈"
            WhatsAppService.send_message(app, 'reminder', f"[24h] {msg}")
            self.stdout.write(self.style.SUCCESS(f'Lembrete 24h enviado para {app.client}'))

        # 2. Reminders for 1h
        limit_1h = now + timedelta(hours=1)
        apps_1h = Appointment.objects.filter(
            status='confirmed',
            date_time__gt=now,
            date_time__lte=limit_1h
        ).exclude(notifications__type='reminder', notifications__message__contains='1h')

        for app in apps_1h:
            msg = f"Olá, seu agendamento é em 1 hora ({app.date_time.strftime('%H:%M')}). Já estamos te esperando! 💈"
            WhatsAppService.send_message(app, 'reminder', f"[1h] {msg}")
            self.stdout.write(self.style.SUCCESS(f'Lembrete 1h enviado para {app.client}'))
