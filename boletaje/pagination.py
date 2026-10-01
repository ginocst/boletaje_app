"""Paginación global de la API: ?page=2&page_size=9 (máximo 100 por página)."""
from rest_framework.pagination import PageNumberPagination


class PaginaEstandar(PageNumberPagination):
    """Paginación por número de página; el cliente puede ajustar el tamaño con ?page_size=."""
    page_size = 9
    page_size_query_param = 'page_size'
    max_page_size = 100
