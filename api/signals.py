from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Appointment
from .whatsapp_service import WhatsAppService

@receiver(post_save, sender=Appointment)
def trigger_notifications(sender, instance, created, **kwargs):
    if created:
        # Send confirmation for new appointments
        WhatsAppService.send_confirmation(instance)
    else:
        # Check for status changes
        if instance.status == 'cancelled':
            WhatsAppService.send_cancellation(instance)
        elif instance.status == 'completed':
            WhatsAppService.send_post_visit(instance)
