"""
Permisos personalizados (RBAC)
Leen el rol desde el usuario de la BD (request.user), no desde el token:
así un cambio de rol se respeta aunque el token siga vigente.
"""
from rest_framework.permissions import SAFE_METHODS, BasePermission


class EsOrganizador(BasePermission):
    """Permite el acceso solo a usuarios con rol ORGANIZADOR."""
    message = 'Solo los organizadores pueden realizar esta acción.'

    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and u.rol == 'ORGANIZADOR')


class EsEspectador(BasePermission):
    """Permite el acceso solo a usuarios con rol ESPECTADOR."""
    message = 'Solo los espectadores pueden realizar esta acción.'

    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and u.rol == 'ESPECTADOR')


class LecturaPublicaEscrituraOrganizador(BasePermission):
    """GET/HEAD/OPTIONS: cualquiera. | POST/PUT/PATCH/DELETE: solo organizadores."""
    message = 'Solo los organizadores pueden modificar el catálogo.'

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return EsOrganizador().has_permission(request, view)
