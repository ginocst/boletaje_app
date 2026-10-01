"""
Modelo de usuario
Extendemos AbstractUser para agregar el campo "rol". Con este único campo
resolvemos la autorización por roles (RBAC) de todo el sistema.
"""
from django.contrib.auth.models import AbstractUser
from django.db import models


class Usuario(AbstractUser):
    """Usuario del sistema: el usuario estándar de Django más el campo 'rol'."""
    # CHOICES: los únicos valores permitidos para el rol
    class Rol(models.TextChoices):
        ESPECTADOR = 'ESPECTADOR', 'Espectador'
        ORGANIZADOR = 'ORGANIZADOR', 'Organizador'

    rol = models.CharField(max_length=15, choices=Rol.choices, default=Rol.ESPECTADOR)

    def __str__(self):
        return f'{self.username} ({self.rol})'
