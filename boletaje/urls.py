"""
URLs raíz del proyecto.
"""
from django.urls import include, path, re_path
from django.views.generic import RedirectView, TemplateView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    # Páginas HTML: solo renderizan un template; los datos vienen de la API vía JS
    path('', TemplateView.as_view(template_name='inicio.html'), name='inicio'),
    path('eventos/', TemplateView.as_view(template_name='eventos.html'), name='eventos'),
    path('eventos/<int:pk>/', TemplateView.as_view(template_name='evento_detalle.html'), name='evento_detalle'),
    path('carro/', TemplateView.as_view(template_name='carro.html'), name='carro'),
    path('mis-entradas/', TemplateView.as_view(template_name='mis_entradas.html'), name='mis_entradas'),
    path('organizador/', TemplateView.as_view(template_name='organizador.html'), name='organizador'),
    path('login/', TemplateView.as_view(template_name='login.html'), name='login'),
    path('registro/', TemplateView.as_view(template_name='registro.html'), name='registro'),

    # API REST
    path('api/auth/', include('cuentas.urls')),
    path('api/', include('eventos.urls')),
    path('api/', include('compras.urls')),

    # Documentación OpenAPI
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger'),

    # Repath: cualquier URL inexistente (ej: /xxx) redirige a la landing, sin error 404
    re_path(r'^.*$', RedirectView.as_view(pattern_name='inicio')),
]