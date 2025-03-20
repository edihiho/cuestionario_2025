from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('examen/', views.realizar_examen, name='realizar_examen'),
    path('resultado/<int:examen_id>/', views.resultado_examen, name='resultado_examen'),
    # Agrega más rutas según necesidades (registro, panel admin personalizado, etc.)
]
