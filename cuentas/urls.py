"""Rutas de autenticación (cuelgan de /api/auth/)."""
from django.urls import path

from .views import LoginView, LogoutView, RefreshView, RegistroView

urlpatterns = [
    path('registro/', RegistroView.as_view(), name='registro_api'),
    path('login/', LoginView.as_view(), name='login_api'),
    path('refresh/', RefreshView.as_view(), name='refresh_api'),
    path('logout/', LogoutView.as_view(), name='logout_api'),
]
