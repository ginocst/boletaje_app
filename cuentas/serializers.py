"""
Serializadores de autenticación
"""
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, TokenRefreshSerializer

from .models import Usuario


class TokenConRolSerializer(TokenObtainPairSerializer):
    """Login JWT: agrega el rol (claim personalizado) al payload del token."""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user) # token estándar (user_id...)
        token['rol'] = user.rol # claim personalizado dentro del token
        token['username'] = user.username
        return token

    def validate(self, attrs):
        data = super().validate(attrs) # genera {'refresh': ..., 'access': ...}
        data['rol'] = self.user.rol # el rol también viaja en el cuerpo de la respuesta
        data['username'] = self.user.username
        return data


class RefreshSerializer(TokenRefreshSerializer):
    """Renovación del access token; el refresh es opcional en el cuerpo porque la vista puede tomarlo de la cookie."""
    # Opcional: si no viene en el cuerpo, la vista lo toma de la cookie HttpOnly
    refresh = serializers.CharField(required=False)


class LogoutSerializer(serializers.Serializer):
    """Cuerpo opcional del logout (documenta el campo en Swagger)."""
    refresh = serializers.CharField(required=False) # igual que arriba: cuerpo o cookie


class RegistroSerializer(serializers.ModelSerializer):
    """Registro de usuarios: valida la contraseña y la guarda con hash."""
    # write_only: la contraseña se recibe pero nunca se devuelve
    password = serializers.CharField(write_only=True)

    class Meta:
        model = Usuario
        fields = ['username', 'email', 'password', 'rol']

    def validate(self, attrs):
        # Aplica los validadores de settings.AUTH_PASSWORD_VALIDATORS
        try:
            validate_password(attrs['password'], user=Usuario(username=attrs['username'], email=attrs.get('email', '')))
        except DjangoValidationError as e:
            raise serializers.ValidationError({'password': list(e.messages)})
        return attrs

    def create(self, validated_data):
        # create_user encripta la contraseña (hash). Al guardar el usuario,
        # una señal (compras/signals.py) le crea su carro automáticamente.
        return Usuario.objects.create_user(**validated_data)
