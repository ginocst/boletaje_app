"""Rutas del catálogo (cuelgan de /api/)."""
from rest_framework.routers import SimpleRouter

from .views import EventoViewSet, RecintoViewSet, SectorViewSet

# SimpleRouter genera automáticamente las rutas CRUD de cada ViewSet
router = SimpleRouter()
router.register('eventos', EventoViewSet, basename='evento')
router.register('sectores', SectorViewSet, basename='sector')
router.register('recintos', RecintoViewSet, basename='recinto')

urlpatterns = router.urls
