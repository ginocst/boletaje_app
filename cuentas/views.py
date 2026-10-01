"""
Vistas de autenticación: registro, login, refresh y logout.

El refresh token viaja de dos formas:
  - En el cuerpo JSON de la respuesta: para clientes de API (Swagger, curl, apps).
  - En una cookie HttpOnly: para el sitio web. JavaScript no puede leerla, así que un
    ataque XSS no logra robarla. El access token, en cambio, el navegador solo lo
    guarda en memoria (ver static/js/app.js).
"""
from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import CreateAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .serializers import (LogoutSerializer, RefreshSerializer, RegistroSerializer, TokenConRolSerializer)

COOKIE_REFRESH = 'refresh_token'
COOKIE_RUTA = '/api/auth/' # el navegador solo envía la cookie a estos endpoints


def poner_cookie_refresh(response, refresh):
    response.set_cookie(
        COOKIE_REFRESH, refresh,
        max_age=int(settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'].total_seconds()),
        httponly=True, # inaccesible desde JavaScript
        samesite='Lax', # no se envía en peticiones POST desde otros sitios (anti-CSRF)
        secure=not settings.DEBUG, # en producción, solo por HTTPS
        path=COOKIE_RUTA,
    )


def refresh_de(request):
    """El refresh puede venir en el cuerpo (clientes API) o en la cookie (sitio web)."""
    return request.data.get('refresh') or request.COOKIES.get(COOKIE_REFRESH)


class RegistroView(CreateAPIView):
    """Crea un usuario (Espectador u Organizador)."""
    serializer_class = RegistroSerializer
    authentication_classes = []
    permission_classes = [AllowAny]


class LoginView(TokenObtainPairView):
    """Devuelve access + refresh (con el rol dentro del token) y deja el refresh en la cookie."""
    serializer_class = TokenConRolSerializer

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == status.HTTP_200_OK:
            poner_cookie_refresh(response, response.data['refresh'])
        return response


class RefreshView(TokenRefreshView):
    """Entrega un access nuevo usando el refresh del cuerpo o de la cookie."""
    serializer_class = RefreshSerializer

    def post(self, request, *args, **kwargs):
        refresh = refresh_de(request)
        if not refresh:
            raise InvalidToken('No hay refresh token.')
        serializer = self.get_serializer(data={'refresh': refresh})
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as e:
            raise InvalidToken(e.args[0])
        return Response(serializer.validated_data)


class LogoutView(APIView):
    """
    Logout: invalida el refresh token (lista negra) y borra la cookie. El carro no se
    toca: vive en PostgreSQL asociado al usuario, no a la sesión.
    """
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(request=LogoutSerializer, responses={205: None})
    def post(self, request):
        refresh = refresh_de(request)
        if refresh:
            try:
                RefreshToken(refresh).blacklist()
            except TokenError:
                pass # ya estaba vencido o invalidado: la sesión se cierra igual
        response = Response(status=status.HTTP_205_RESET_CONTENT)
        response.delete_cookie(COOKIE_REFRESH, path=COOKIE_RUTA)
        return response