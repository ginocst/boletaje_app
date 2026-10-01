"""Configuración de la app compras: al iniciar Django registra las señales (creación del carro)."""
from django.apps import AppConfig


class ComprasConfig(AppConfig):
    """Registro de la app 'compras' en Django."""
    name = 'compras'

    def ready(self):
        # Registra las señales al iniciar Django
        from . import signals