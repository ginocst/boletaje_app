"""
Modelos de compra
  Usuario 1 ---- 1 Carro  1 ---- N ItemCarro N ---- 1 Sector (carro persistente)
  Usuario 1 ---- N Orden  1 ---- N DetalleOrden N ---- 1 Sector (historial de compras)
                   Orden  1 ---- N Entrada (ticket con UUID único)
  Organizador 1 ---- N Orden (cada orden pertenece a un organizador: solo él la gestiona)

Ciclo de vida
  0) Carro: estado ACTIVO mientras se agregan/quitan ítems (LIQUIDADO justo tras el checkout).
  1) Checkout: Carro.confirmar() -> Órdenes PENDIENTE (no toca el stock).
  2) Pago: Orden.cambiar_estado(PAGADO) -> valida y DESCUENTA el stock, emite las entradas.
  3) Cancelar: Orden.cambiar_estado(CANCELADO) -> si estaba PAGADA, REPONE el stock.
"""
import uuid
from collections import defaultdict

from django.conf import settings
from django.db import models, transaction
from django.db.models import F

from eventos.models import Sector


class StockInsuficiente(Exception):
    """Se lanza cuando un sector no tiene entradas suficientes al momento de pagar."""


# Carro persistente (1 a 1 con el usuario, siempre activo, guardado en PostgreSQL)
class Carro(models.Model):
    """Carro de compras persistente del usuario."""

    # Choices: estado del carro
    class Estado(models.TextChoices):
        ACTIVO = 'ACTIVO', 'Activo' # se están agregando o quitando ítems
        LIQUIDADO = 'LIQUIDADO', 'Liquidado' # ya se hizo el checkout: quedó vacío (vuelve a ACTIVO al agregar)

    # OneToOne: cada usuario tiene un solo carro, sin importar dispositivo ni sesión
    usuario = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='carro')
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.ACTIVO)

    @property
    def total(self):
        return sum((i.subtotal for i in self.items.select_related('sector')), 0)

    @transaction.atomic
    def confirmar(self):
        """
        CHECKOUT: liquida el carro y lo convierte en órdenes PENDIENTE (registro histórico).
        Se crea una orden por organizador, para que cada uno gestione solo sus ventas.
        NO descuenta stock: eso ocurre recién cuando la orden pasa a PAGADO.
        """
        grupos = defaultdict(list)
        for item in self.items.select_related('sector__evento'):
            grupos[item.sector.evento.organizador_id].append(item)

        ordenes = []
        for organizador_id, items in grupos.items():
            orden = Orden.objects.create(usuario=self.usuario, organizador_id=organizador_id,
                                        total=sum(i.subtotal for i in items))
            # El detalle guarda una copia del precio del momento
            DetalleOrden.objects.bulk_create([
                DetalleOrden(orden=orden, sector=i.sector, cantidad=i.cantidad, precio_unitario=i.sector.precio)
                for i in items])
            ordenes.append(orden)

        if ordenes:
            self.items.all().delete()   # el contenido del carro se liquida: queda vacío
            self.estado = self.Estado.LIQUIDADO
            self.save(update_fields=['estado'])
        return ordenes


class ItemCarro(models.Model):
    """Línea del carro: un sector y su cantidad."""
    carro = models.ForeignKey(Carro, on_delete=models.CASCADE, related_name='items')
    sector = models.ForeignKey(Sector, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField(default=1)

    class Meta:
        # Un sector aparece una sola vez por carro (si se repite, se suma la cantidad)
        constraints = [models.UniqueConstraint(fields=['carro', 'sector'], name='item_unico_por_sector')]

    @property
    def subtotal(self):
        return self.sector.precio * self.cantidad


# Orden (registro histórico de la compra)
class Orden(models.Model):
    # Choices: estados de la transacción
    class Estado(models.TextChoices):
        PENDIENTE = 'PENDIENTE', 'Pendiente'
        PAGADO = 'PAGADO', 'Pagado'
        ENTREGADO = 'ENTREGADO', 'Entregado'
        CANCELADO = 'CANCELADO', 'Cancelado'

    # Transiciones permitidas: estado actual -> estados a los que puede pasar
    TRANSICIONES = {
        Estado.PENDIENTE: [Estado.PAGADO, Estado.CANCELADO],
        Estado.PAGADO: [Estado.ENTREGADO, Estado.CANCELADO],
        Estado.ENTREGADO: [],
        Estado.CANCELADO: [],
    }

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='ordenes')
    organizador = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='ventas')
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.PENDIENTE)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-creado']

    @transaction.atomic # todo el método es una transacción, o se hace completo o no se hace nada
    def cambiar_estado(self, nuevo):
        """
        Único punto de entrada para cambiar el estado de una orden.
        Valida la transición y aplica la lógica de stock que corresponda.
        """
        # 1) Bloquea la fila de la orden (SELECT ... FOR UPDATE). Si llegan dos cambios a la
        # vez (por ejemplo: pagar dos veces), el segundo espera y luego ve el estado ya actualizado.
        Orden.objects.select_for_update().get(pk=self.pk)
        self.refresh_from_db(fields=['estado'])

        # 2) Valida que la transición esté permitida
        if nuevo not in self.TRANSICIONES[self.estado]:
            raise ValueError(f'No se puede pasar una orden de {self.estado} a {nuevo}.')

        # 3) Lógica de inventario
        if nuevo == self.Estado.PAGADO:
            self._descontar_stock_y_emitir_entradas()
        elif nuevo == self.Estado.CANCELADO:
            self._reponer_stock()

        self.estado = nuevo
        self.save(update_fields=['estado'])

    def _descontar_stock_y_emitir_entradas(self):
        """PENDIENTE -> PAGADO: valida el stock de cada sector, lo descuenta y emite los tickets."""
        detalles = list(self.detalles.select_related('sector'))

        # Bloquea las filas de los sectores hasta terminar la transacción: dos compras
        # simultáneas no pueden vender la misma entrada (se ordenan por id para evitar deadlocks).
        ids = [d.sector_id for d in detalles]
        sectores = {s.pk: s for s in Sector.objects.select_for_update().filter(pk__in=ids).order_by('pk')}

        for d in detalles:
            sector = sectores[d.sector_id]
            if sector.stock < d.cantidad:
                # Al lanzar la excepción, la transacción completa se revierte
                raise StockInsuficiente(
                    f'Stock insuficiente en "{sector}": solicitadas {d.cantidad}, disponibles {sector.stock}.')
            sector.stock -= d.cantidad
            sector.save(update_fields=['stock'])

        # Un ticket por entrada. El UUID se genera solo (default=uuid4).
        Entrada.objects.bulk_create(
            [Entrada(orden=self, sector=d.sector) for d in detalles for _ in range(d.cantidad)])

    def _reponer_stock(self):
        """Si la orden estaba PAGADA, devuelve las entradas al catálogo. Si estaba PENDIENTE, no había descontado nada."""
        if self.estado == self.Estado.PAGADO:
            for d in self.detalles.all():
                # F(): suma directo en la BD, sin leer antes (seguro ante concurrencia)
                Sector.objects.filter(pk=d.sector_id).update(stock=F('stock') + d.cantidad)


class DetalleOrden(models.Model):
    """Copia de lo comprado. Guarda el precio del momento (el precio del sector puede cambiar)."""
    orden = models.ForeignKey(Orden, on_delete=models.CASCADE, related_name='detalles')
    sector = models.ForeignKey(Sector, on_delete=models.PROTECT) # PROTECT: protege el historial
    cantidad = models.PositiveIntegerField()
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)


class Entrada(models.Model):
    """Ticket individual con código único. Es válido solo si su orden está PAGADO o ENTREGADO."""
    orden = models.ForeignKey(Orden, on_delete=models.CASCADE, related_name='entradas')
    sector = models.ForeignKey(Sector, on_delete=models.PROTECT)
    codigo = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)