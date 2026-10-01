"""
Cada vez que se crea un usuario, se le crea su carro (relación 1 a 1).
"""
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Carro


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def crear_carro_al_crear_usuario(sender, instance, created, **kwargs):
    if created:
        Carro.objects.create(usuario=instance)
