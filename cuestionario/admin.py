from django.contrib import admin
from .models import Usuario, Pregunta, Opcion, Examen, Respuesta

@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'correo', 'rol', 'tipo_usuario', 'localidad')
    search_fields = ('nombre', 'correo')

@admin.register(Pregunta)
class PreguntaAdmin(admin.ModelAdmin):
    list_display = ('id', 'pregunta', 'categoria', 'tipo_usuario')
    search_fields = ('pregunta', 'categoria')

@admin.register(Opcion)
class OpcionAdmin(admin.ModelAdmin):
    list_display = ('id', 'pregunta', 'opcion', 'es_correcta')
    list_filter = ('es_correcta',)

@admin.register(Examen)
class ExamenAdmin(admin.ModelAdmin):
    list_display = ('id', 'usuario', 'fecha', 'duracion')

@admin.register(Respuesta)
class RespuestaAdmin(admin.ModelAdmin):
    list_display = ('id', 'examen', 'pregunta', 'opcion', 'es_correcta')
# models here.
