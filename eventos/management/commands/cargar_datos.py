"""
Comando para cargar datos de prueba: python manage.py cargar_datos

Es idempotente: se puede ejecutar varias veces sin duplicar registros.
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from cuentas.models import Usuario
from eventos.models import Evento, Recinto, Sector

CLAVE = 'Clave1234'

# (nombre, ciudad, dirección)
RECINTOS = [
    ('Estadio Nacional', 'Santiago', 'Av. Grecia 2001'),
    ('Teatro Municipal', 'Viña del Mar', 'Av. Libertad 250'),
    ('Arena Sur', 'Concepción', 'Av. Los Carrera 1200'),
]

# (nombre, artista, categoría, días desde hoy, índice recinto, organizador, [(sector, precio, stock)])
EVENTOS = [
    ('Noche de Rock', 'Los Vientos del Sur', 'CONCIERTO', 15, 0, 'organizador1',
     [('Cancha General', 25000, 100), ('Tribuna', 40000, 50), ('VIP', 90000, 5)]),
    ('Festival Costa Viva', 'Varios artistas', 'FESTIVAL', 30, 1, 'organizador1',
     [('Entrada General', 35000, 200), ('Pase VIP', 120000, 20)]),
    ('Gira Nova Pulse', 'Nova Pulse', 'CONCIERTO', 45, 2, 'organizador1',
     [('Cancha', 30000, 80), ('Platea', 55000, 40)]),
    ('El Fantasma de la Ópera', 'Compañía Nacional', 'TEATRO', 20, 1, 'organizador2',
     [('Platea Alta', 28000, 60), ('Platea Baja', 45000, 30)]),
    ('Clásico Universitario', 'Selecciones U', 'DEPORTE', 10, 0, 'organizador2',
     [('Galería', 12000, 300), ('Andes', 22000, 100)]),
    # Stock mínimo a propósito: sirve para probar el rechazo por stock insuficiente
    ('Show Íntimo Acústico', 'Luna Roja', 'CONCIERTO', 7, 2, 'organizador1',
     [('Mesa Frontal', 60000, 2)]),
]


class Command(BaseCommand):
    """Comando que carga datos de prueba (idempotente)."""
    help = 'Carga usuarios, recintos, eventos y sectores de prueba.'

    def handle(self, *args, **options):
        # Usuarios (su carro se crea solo por la señal post_save)
        usuarios = {}
        for username, rol in [('organizador1', 'ORGANIZADOR'), ('organizador2', 'ORGANIZADOR'),
        ('espectador1', 'ESPECTADOR'), ('espectador2', 'ESPECTADOR')]:
            user, creado = Usuario.objects.get_or_create(username=username, defaults={'rol': rol})
            if creado:
                user.set_password(CLAVE)
                user.save()
            usuarios[username] = user

        # Recintos
        recintos = [Recinto.objects.get_or_create(nombre=n, defaults={'ciudad': c, 'direccion': d})[0]
                    for n, c, d in RECINTOS]

        # Eventos y sectores
        for nombre, artista, categoria, dias, idx, organizador, sectores in EVENTOS:
            evento, creado = Evento.objects.get_or_create(
                nombre=nombre,
                defaults={'organizador': usuarios[organizador], 'recinto': recintos[idx],
                'artista': artista, 'categoria': categoria,
                'fecha_hora': timezone.now() + timedelta(days=dias),
                'descripcion': f'{artista} en vivo. ¡No te quedes sin tu entrada!'})
            if creado:
                for s_nombre, precio, stock in sectores:
                    Sector.objects.create(evento=evento, nombre=s_nombre, precio=precio, stock=stock)

        self.stdout.write(self.style.SUCCESS(
            f'Datos cargados. Usuarios: organizador1, organizador2, espectador1, espectador2 (clave: {CLAVE})'))
