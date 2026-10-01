"""
Serializadores del catálogo
"""
from rest_framework import serializers

from .models import Evento, Recinto, Sector


class RecintoSerializer(serializers.ModelSerializer):
    """Datos de un recinto."""
    class Meta:
        model = Recinto
        fields = ['id', 'nombre', 'ciudad', 'direccion']


class SectorSerializer(serializers.ModelSerializer):
    """Sector de un evento: localidad, precio y stock."""
    class Meta:
        model = Sector
        fields = ['id', 'evento', 'nombre', 'precio', 'stock']
        read_only_fields = ['evento'] # el evento lo define la URL, no el cliente


class EventoSerializer(serializers.ModelSerializer):
    """Evento con datos calculados de solo lectura para el frontend."""
    # Campos de solo lectura para que el frontend no tenga que hacer más consultas
    recinto_detalle = RecintoSerializer(source='recinto', read_only=True)
    organizador = serializers.CharField(source='organizador.username', read_only=True)
    categoria_display = serializers.CharField(source='get_categoria_display', read_only=True)
    precio_desde = serializers.SerializerMethodField()

    class Meta:
        model = Evento
        fields = ['id', 'nombre', 'artista', 'categoria', 'categoria_display', 'fecha_hora',
        'descripcion', 'recinto', 'recinto_detalle', 'organizador', 'precio_desde']

    def get_precio_desde(self, obj) -> float:
        # Precio del sector más barato (usa prefetch_related, sin consultas extra)
        precios = [s.precio for s in obj.sectores.all()]
        return float(min(precios)) if precios else None
