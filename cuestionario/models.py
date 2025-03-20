from django.db import models
from django.utils import timezone

# Opción 1: Usar un modelo de Usuario personalizado
# Opción 2: Usar el modelo de Django (User) y añadir campos extra mediante un Profile. 
# Aquí haré algo sencillo (User Personalizado). 
# Sin embargo, en producción, se recomienda usar AUTH_USER_MODEL para integrarlo bien con Django.

class Usuario(models.Model):
    ROLES = (
        ('admin', 'Admin'),
        ('usuario', 'Usuario'),
    )
    TIPOS_USUARIO = (
        ('OYM', 'OYM'),
        ('LABORATORIO', 'LABORATORIO'),
    )
    LOCALIDADES = (
        ('Risaralda', 'Risaralda'),
        ('Quindio', 'Quindio'),
        ('Caldas', 'Caldas'),
    )

    nombre = models.CharField(max_length=100)
    correo = models.EmailField(unique=True)
    # En un proyecto real, se debe usar contraseña hasheada, 
    # o integrar con django.contrib.auth
    contraseña = models.CharField(max_length=128)
    rol = models.CharField(max_length=10, choices=ROLES, default='usuario')
    tipo_usuario = models.CharField(max_length=15, choices=TIPOS_USUARIO, default='OYM')
    localidad = models.CharField(max_length=15, choices=LOCALIDADES, default='Risaralda')

    def __str__(self):
        return f"{self.nombre} ({self.correo})"


class Pregunta(models.Model):
    TIPOS_USUARIO = (
        ('OYM', 'OYM'),
        ('LABORATORIO', 'LABORATORIO'),
    )
    pregunta = models.TextField()
    categoria = models.CharField(max_length=100)
    tipo_usuario = models.CharField(max_length=15, choices=TIPOS_USUARIO)

    def __str__(self):
        return self.pregunta[:50]  # Mostramos solo los primeros 50 caracteres


class Opcion(models.Model):
    pregunta = models.ForeignKey(Pregunta, on_delete=models.CASCADE)
    opcion = models.CharField(max_length=255)
    es_correcta = models.BooleanField(default=False)

    def __str__(self):
        return f"Opción para {self.pregunta}: {self.opcion}"


class Examen(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    fecha = models.DateTimeField(default=timezone.now)
    # duracion en segundos
    duracion = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f"Examen #{self.id} de {self.usuario}"


class Respuesta(models.Model):
    examen = models.ForeignKey(Examen, on_delete=models.CASCADE)
    pregunta = models.ForeignKey(Pregunta, on_delete=models.CASCADE)
    opcion = models.ForeignKey(Opcion, on_delete=models.CASCADE)
    es_correcta = models.BooleanField(default=False)

    def __str__(self):
        return f"Resp #{self.id} - Examen {self.examen.id} - Pregunta {self.pregunta.id}"
