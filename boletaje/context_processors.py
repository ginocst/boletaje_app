"""Este archivo pone los datos del alumno disponibles en todos los templates."""
from django.conf import settings


def datos_alumno(request):
    return {'ALUMNO': settings.DATOS_ALUMNO}
