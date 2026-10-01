"""
Filtros de órdenes: /api/compras/?estado=PAGADO&desde=2026-01-01
"""
from django_filters import rest_framework as filters

from .models import Orden


class OrdenFilter(filters.FilterSet):
    """Filtros de órdenes: estado y rango de fechas de creación."""
    desde = filters.DateFilter(field_name='creado', lookup_expr='date__gte')
    hasta = filters.DateFilter(field_name='creado', lookup_expr='date__lte')

    class Meta:
        model = Orden
        fields = ['estado']
