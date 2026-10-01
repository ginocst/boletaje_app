"""
Serializadores de carro, órdenes y entradas
"""
from rest_framework import serializers

from .models import Carro, DetalleOrden, Entrada, ItemCarro, Orden


class ItemCarroSerializer(serializers.ModelSerializer):
    """Ítem del carro con datos del sector para mostrar en pantalla."""
    sector_nombre = serializers.CharField(source='sector.nombre', read_only=True)
    evento = serializers.CharField(source='sector.evento.nombre', read_only=True)
    precio = serializers.DecimalField(source='sector.precio', max_digits=10, decimal_places=2, read_only=True)
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = ItemCarro
        fields = ['id', 'sector', 'cantidad', 'sector_nombre', 'evento', 'precio', 'subtotal']
        extra_kwargs = {'cantidad': {'min_value': 1}} # no se aceptan cantidades 0


class CarroSerializer(serializers.ModelSerializer):
    """Carro con sus ítems y el total."""
    items = ItemCarroSerializer(many=True, read_only=True)
    total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = Carro
        fields = ['id', 'estado', 'items', 'total']


class DetalleOrdenSerializer(serializers.ModelSerializer):
    """Línea de una orden (copia de lo comprado)."""
    sector_nombre = serializers.CharField(source='sector.nombre', read_only=True)
    evento = serializers.CharField(source='sector.evento.nombre', read_only=True)

    class Meta:
        model = DetalleOrden
        fields = ['sector_nombre', 'evento', 'cantidad', 'precio_unitario']


class OrdenSerializer(serializers.ModelSerializer):
    """Orden con su detalle."""
    usuario = serializers.CharField(source='usuario.username', read_only=True)
    detalles = DetalleOrdenSerializer(many=True, read_only=True)

    class Meta:
        model = Orden
        fields = ['id', 'usuario', 'estado', 'total', 'creado', 'detalles']


class EstadoOrdenSerializer(serializers.Serializer):
    """Cuerpo de PATCH /api/compras/{id}/estado/."""
    estado = serializers.ChoiceField(choices=Orden.Estado.choices)


class PagarSerializer(serializers.Serializer):
    """Cuerpo (opcional) de POST /api/compras/pagar/: la orden pendiente que se paga."""
    orden = serializers.IntegerField(
        required=False,
        help_text='Id de una orden PENDIENTE (la entrega el checkout). Si se omite, se paga directamente el carro.')


class EntradaSerializer(serializers.ModelSerializer):
    """Ticket emitido, con datos del evento para mostrar."""
    evento = serializers.CharField(source='sector.evento.nombre', read_only=True)
    artista = serializers.CharField(source='sector.evento.artista', read_only=True)
    fecha_hora = serializers.DateTimeField(source='sector.evento.fecha_hora', read_only=True)
    recinto = serializers.CharField(source='sector.evento.recinto.nombre', read_only=True)
    sector_nombre = serializers.CharField(source='sector.nombre', read_only=True)
    estado_orden = serializers.CharField(source='orden.estado', read_only=True)

    class Meta:
        model = Entrada
        fields = ['codigo', 'evento', 'artista', 'fecha_hora', 'recinto', 'sector_nombre', 'estado_orden']
