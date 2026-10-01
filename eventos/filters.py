"""
Filtros (django-filter) para el catálogo de eventos.
Ejemplo: /api/eventos/?categoria=CONCIERTO&precio_max=30000&ciudad=santiago
"""
from django_filters import rest_framework as filters

from .models import Evento


class EventoFilter(filters.FilterSet):
    """Filtros del catálogo: categoría, recinto, precio, fechas, ciudad y 'mios'."""
    # Rango de precio: se busca en los sectores del evento (distinct evita duplicados por el JOIN)
    precio_min = filters.NumberFilter(field_name='sectores__precio', lookup_expr='gte', distinct=True)
    precio_max = filters.NumberFilter(field_name='sectores__precio', lookup_expr='lte', distinct=True)
    # Rango de fechas
    desde = filters.DateFilter(field_name='fecha_hora', lookup_expr='date__gte')
    hasta = filters.DateFilter(field_name='fecha_hora', lookup_expr='date__lte')
    # Ciudad del recinto (búsqueda parcial, sin distinguir mayúsculas)
    ciudad = filters.CharFilter(field_name='recinto__ciudad', lookup_expr='icontains')
    # ?mios=true -> solo los eventos del organizador autenticado
    mios = filters.BooleanFilter(method='filtrar_mios')

    class Meta:
        model = Evento
        fields = ['categoria', 'recinto'] # filtros exactos automáticos

    def filtrar_mios(self, queryset, name, value):
        user = self.request.user
        if value and user.is_authenticated:
            return queryset.filter(organizador=user)
        return queryset
