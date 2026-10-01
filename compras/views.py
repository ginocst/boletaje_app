"""
Vistas de compra
  Espectador:  GET/POST/DELETE /api/carro-tickets/ , DELETE /api/carro-tickets/{id}/
               POST /api/compras/pagar/ (directo desde el carro, o una orden creada con checkout)
               POST /api/compras/checkout/ , GET /api/mis-entradas/
  Ambos roles: GET /api/compras/   (espectador: sus compras / organizador: las ventas de sus eventos)
  Organizador: PATCH /api/compras/{id}/estado/
"""
from django.db import transaction
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import GenericAPIView, ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from cuentas.permissions import EsEspectador, EsOrganizador

from .filters import OrdenFilter
from .models import Entrada, ItemCarro, Orden, StockInsuficiente
from .serializers import (CarroSerializer, EntradaSerializer, EstadoOrdenSerializer,
ItemCarroSerializer, OrdenSerializer, PagarSerializer)


# Carro: todo se guarda en PostgreSQL, ligado al usuario del token
class CarroView(APIView):
    permission_classes = [EsEspectador]

    @extend_schema(responses=CarroSerializer)
    def get(self, request):
        """Devuelve el carro del usuario (sus ítems se conservan tras logout o en otro dispositivo)."""
        return Response(CarroSerializer(request.user.carro).data)

    @extend_schema(request=ItemCarroSerializer, responses={201: CarroSerializer})
    def post(self, request):
        """
        Agrega entradas al carro. Si el sector ya está en el carro, suma la cantidad (sin duplicar).
        Solo se acepta lo que el stock permite; el stock NO se descuenta aquí, sino al pagar.
        """
        serializer = ItemCarroSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        carro = request.user.carro
        sector = serializer.validated_data['sector']

        item = carro.items.filter(sector=sector).first()
        en_carro = item.cantidad if item else 0
        cantidad = en_carro + serializer.validated_data['cantidad']
        if cantidad > sector.stock:
            return Response(
                {'detail': f'Solo quedan {sector.stock} entradas en "{sector}" (ya tienes {en_carro} en tu carro).'},
                status=status.HTTP_400_BAD_REQUEST)

        if item:
            item.cantidad = cantidad
            item.save(update_fields=['cantidad'])
        else:
            ItemCarro.objects.create(carro=carro, sector=sector, cantidad=cantidad)

        if carro.estado != carro.Estado.ACTIVO: # tras un checkout, agregar un ítem lo reactiva
            carro.estado = carro.Estado.ACTIVO
            carro.save(update_fields=['estado'])
        return Response(CarroSerializer(carro).data, status=status.HTTP_201_CREATED)

    @extend_schema(operation_id='carro_tickets_vaciar', responses={204: None})
    def delete(self, request):
        """Vacía el carro."""
        request.user.carro.items.all().delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CarroItemView(APIView):
    """Quita un ítem puntual del carro."""
    permission_classes = [EsEspectador]

    @extend_schema(operation_id='carro_tickets_quitar_item', responses={204: None})
    def delete(self, request, pk):
        """Quita un ítem del carro (solo si pertenece al carro del usuario)."""
        item = get_object_or_404(ItemCarro, pk=pk, carro=request.user.carro)
        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# Checkout y pago
def aplicar_estado(orden, nuevo):
    """Cambia el estado de una orden y traduce los errores del negocio a respuestas HTTP."""
    try:
        orden.cambiar_estado(nuevo)
    except StockInsuficiente as e:
        return Response({'detail': str(e)}, status=status.HTTP_409_CONFLICT) # pago rechazado
    except ValueError as e: # transición no permitida
        return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    return Response(OrdenSerializer(orden).data)


class CheckoutView(APIView):
    """Checkout: convierte el carro en órdenes pendientes."""
    permission_classes = [EsEspectador]

    @extend_schema(request=None, responses={201: OrdenSerializer(many=True)})
    def post(self, request):
        """Confirma el pedido: el carro se convierte en órdenes PENDIENTE. Todavía no se paga ni se descuenta stock."""
        ordenes = request.user.carro.confirmar()
        if not ordenes:
            return Response({'detail': 'El carro está vacío.'}, status=status.HTTP_400_BAD_REQUEST)
        return Response(OrdenSerializer(ordenes, many=True).data, status=status.HTTP_201_CREATED)


class PagarView(APIView):
    """Pago (simulado): de una orden pendiente o directamente desde el carro."""
    permission_classes = [EsEspectador]

    @extend_schema(request=PagarSerializer, responses=OrdenSerializer(many=True))
    def post(self, request):
        """
        Procesa el pago (simulado) y pasa las órdenes a PAGADO. Dos modos:
          - Con {"orden": id}: paga esa orden PENDIENTE propia (la creó antes /checkout/).
            Sin stock suficiente responde 409, la orden sigue PENDIENTE y no se descuenta nada.
          - Sin cuerpo (pago directo): hace el checkout del carro y paga todo en UNA transacción.
            Si algo falla, no queda nada guardado y el carro sigue intacto.
        """
        serializer = PagarSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        orden_id = serializer.validated_data.get('orden')

        try:
            with transaction.atomic(): # si una orden falla, se revierte todo lo anterior
                if orden_id:
                    ordenes = [get_object_or_404(Orden, pk=orden_id, usuario=request.user)]
                else:
                    ordenes = request.user.carro.confirmar()
                    if not ordenes:
                        return Response({'detail': 'El carro está vacío.'}, status=status.HTTP_400_BAD_REQUEST)
                for orden in ordenes:
                    orden.cambiar_estado(Orden.Estado.PAGADO)
        except StockInsuficiente as e:
            return Response({'detail': str(e)}, status=status.HTTP_409_CONFLICT)
        except ValueError as e: # transición no permitida (ej: la orden ya estaba pagada)
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(OrdenSerializer(ordenes, many=True).data)


# Consulta de órdenes y cambio de estado
class OrdenListView(ListAPIView):
    queryset = Orden.objects.none() # solo para Swagger; el real está en get_queryset()
    serializer_class = OrdenSerializer
    permission_classes = [IsAuthenticated]
    filterset_class = OrdenFilter

    def get_queryset(self):
        user = self.request.user
        # Organizador: sus ventas. Espectador: sus compras.
        qs = Orden.objects.filter(organizador=user) if user.rol == 'ORGANIZADOR' else Orden.objects.filter(usuario=user)
        return qs.select_related('usuario').prefetch_related('detalles__sector__evento')


class OrdenEstadoView(GenericAPIView):
    """Cambio de estado de una venta por parte del organizador."""
    serializer_class = EstadoOrdenSerializer
    permission_classes = [EsOrganizador]

    @extend_schema(responses=OrdenSerializer)
    def patch(self, request, pk):
        """El organizador cambia el estado de sus ventas. PAGADO descuenta stock; CANCELADO lo repone."""
        orden = get_object_or_404(Orden, pk=pk, organizador=request.user)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return aplicar_estado(orden, serializer.validated_data['estado'])


# Mis entradas: tickets válidos del espectador
class MisEntradasView(ListAPIView):
    queryset = Entrada.objects.none() # solo para Swagger; el real está en get_queryset()
    serializer_class = EntradaSerializer
    permission_classes = [EsEspectador]

    def get_queryset(self):
        return (Entrada.objects
                .filter(orden__usuario=self.request.user,
                        orden__estado__in=[Orden.Estado.PAGADO, Orden.Estado.ENTREGADO])
                .select_related('sector__evento__recinto', 'orden')
                .order_by('sector__evento__fecha_hora', 'id'))