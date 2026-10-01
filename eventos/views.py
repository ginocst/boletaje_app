"""
Vistas del catálogo
  Público (incluye al espectador, solo lectura):
GET /api/eventos/ , /api/eventos/{id}/ , /api/eventos/{id}/sectores/ , /api/recintos/
  Organizador (eventos y sectores: solo los propios):
    POST /api/eventos/ , PUT/PATCH/DELETE /api/eventos/{id}/
    POST /api/eventos/{id}/sectores/ , PUT/PATCH /api/sectores/{id}/
    POST /api/recintos/
  Las acciones del espectador (carro, pago, entradas) están en compras/views.py.
"""
from django.db.models import ProtectedError
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from cuentas.permissions import EsOrganizador, LecturaPublicaEscrituraOrganizador

from .filters import EventoFilter
from .models import Evento, Recinto, Sector
from .serializers import EventoSerializer, RecintoSerializer, SectorSerializer


class EventoViewSet(viewsets.ModelViewSet):
    """CRUD de eventos: lectura pública, escritura solo del organizador dueño."""
    queryset = Evento.objects.none() # solo para Swagger; el queryset real está en get_queryset()
    serializer_class = EventoSerializer
    permission_classes = [LecturaPublicaEscrituraOrganizador]
    filterset_class = EventoFilter # filtros
    search_fields = ['nombre', 'artista', 'recinto__nombre'] # ?search=texto
    ordering_fields = ['fecha_hora', 'nombre'] # ?ordering=fecha_hora

    def get_queryset(self):
        # select_related / prefetch_related: evitan consultas repetidas (N+1)
        qs = Evento.objects.select_related('recinto', 'organizador').prefetch_related('sectores')
        # Para modificar o borrar, el organizador solo "ve" sus propios eventos
        if self.action in ('update', 'partial_update', 'destroy'):
            qs = qs.filter(organizador=self.request.user)
        return qs

    def perform_create(self, serializer):
        # El organizador se toma del token, nunca del cuerpo de la petición
        serializer.save(organizador=self.request.user)

    def destroy(self, request, *args, **kwargs):
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            # Sus sectores ya tienen ventas (DetalleOrden usa PROTECT)
            return Response({'detail': 'No se puede eliminar: el evento tiene ventas registradas.'},
                            status=status.HTTP_409_CONFLICT)

    @extend_schema(methods=['GET'], responses=SectorSerializer(many=True))
    @extend_schema(methods=['POST'], request=SectorSerializer, responses={201: SectorSerializer})
    @action(detail=True, methods=['get', 'post'], url_path='sectores', filter_backends=[])
    def sectores(self, request, pk=None):
        """GET público: lista los sectores. POST (solo el organizador dueño): crea un sector."""
        evento = self.get_object()
        if request.method == 'GET':
            return Response(SectorSerializer(evento.sectores.all(), many=True).data)

        if evento.organizador != request.user:
            raise PermissionDenied('Solo el organizador del evento puede agregar sectores.')
        serializer = SectorSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(evento=evento)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class SectorViewSet(mixins.UpdateModelMixin, viewsets.GenericViewSet):
    """PUT/PATCH /api/sectores/{id}/ -> el organizador ajusta precio o stock de SUS sectores."""
    queryset = Sector.objects.none() # solo para Swagger; el real está en get_queryset()
    serializer_class = SectorSerializer
    permission_classes = [EsOrganizador]

    def get_queryset(self):
        return Sector.objects.filter(evento__organizador=self.request.user)


class RecintoViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    """GET público / POST solo organizador."""
    queryset = Recinto.objects.all()
    serializer_class = RecintoSerializer
    permission_classes = [LecturaPublicaEscrituraOrganizador]