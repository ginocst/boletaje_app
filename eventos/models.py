"""
Modelos del catálogo: Recinto -> Evento -> Sector
  Recinto  1 ---- N  Evento
  Evento   1 ---- N  Sector
  Usuario  1 ---- N  Evento
"""
from django.conf import settings
from django.db import models


class Recinto(models.Model):
    """Lugar físico donde se realizan los eventos."""
    nombre = models.CharField(max_length=120)
    ciudad = models.CharField(max_length=80)
    direccion = models.CharField(max_length=200)

    def __str__(self):
        return f'{self.nombre} ({self.ciudad})'


class Evento(models.Model):
    """Evento o concierto publicado por un organizador."""
    # CHOICES: categorías permitidas (también se usan como filtro)
    class Categoria(models.TextChoices):
        CONCIERTO = 'CONCIERTO', 'Concierto'
        FESTIVAL = 'FESTIVAL', 'Festival'
        TEATRO = 'TEATRO', 'Teatro'
        DEPORTE = 'DEPORTE', 'Deporte'

    organizador = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='eventos')
    # PROTECT: no se puede borrar un recinto que tenga eventos
    recinto = models.ForeignKey(Recinto, on_delete=models.PROTECT, related_name='eventos')
    nombre = models.CharField(max_length=150)
    artista = models.CharField(max_length=150)
    categoria = models.CharField(max_length=10, choices=Categoria.choices, default=Categoria.CONCIERTO)
    fecha_hora = models.DateTimeField()
    descripcion = models.TextField(blank=True)

    class Meta:
        ordering = ['fecha_hora']

    def __str__(self):
        return self.nombre


class Sector(models.Model):
    """Localidad de un evento (Cancha, VIP, Tribuna...). 'stock' = entradas disponibles."""
    evento = models.ForeignKey(Evento, on_delete=models.CASCADE, related_name='sectores')
    nombre = models.CharField(max_length=80)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField()

    def __str__(self):
        return f'{self.evento.nombre} - {self.nombre}'