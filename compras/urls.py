"""Rutas de la API de compras (todas cuelgan de /api/)."""
from django.urls import path

from .views import (CarroItemView, CarroView, CheckoutView, MisEntradasView,
                    OrdenEstadoView, OrdenListView, PagarView)

urlpatterns = [
    path('carro-tickets/', CarroView.as_view(), name='carro_api'),
    path('carro-tickets/<int:pk>/', CarroItemView.as_view(), name='carro_item_api'),
    path('compras/', OrdenListView.as_view(), name='compras_api'),
    path('compras/checkout/', CheckoutView.as_view(), name='checkout_api'),
    path('compras/pagar/', PagarView.as_view(), name='pagar_api'),
    path('compras/<int:pk>/estado/', OrdenEstadoView.as_view(), name='estado_api'),
    path('mis-entradas/', MisEntradasView.as_view(), name='mis_entradas_api'),
]
