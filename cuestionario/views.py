from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.utils import timezone
import time

from .models import Usuario, Pregunta, Opcion, Examen, Respuesta

# Ejemplo de una vista de inicio
def home(request):
    return render(request, 'cuestionario/home.html')

def login_view(request):
    if request.method == 'POST':
        correo = request.POST.get('correo')
        password = request.POST.get('contraseña')

        try:
            # Verificamos si el usuario existe en la tabla Usuario:
            usuario = Usuario.objects.get(correo=correo, contraseña=password)
            # (NOTA: Esto no es seguro en producción: hay que usar un método hasheado o el sistema de Django)
            
            # Podrías almacenar en sesión:
            request.session['usuario_id'] = usuario.id
            messages.success(request, f"Bienvenido, {usuario.nombre}")
            return redirect('home')
        except Usuario.DoesNotExist:
            messages.error(request, "Credenciales inválidas.")
            return redirect('login')
    return render(request, 'cuestionario/login.html')

def logout_view(request):
    # Borrar la sesión
    if 'usuario_id' in request.session:
        del request.session['usuario_id']
    messages.info(request, "Has cerrado sesión.")
    return redirect('home')

def realizar_examen(request):
    """
    Ejemplo sencillo de obtención de preguntas y guardado de respuestas.
    """
    # Verificamos si el usuario está en sesión
    usuario_id = request.session.get('usuario_id', None)
    if not usuario_id:
        messages.error(request, "Debes iniciar sesión primero.")
        return redirect('login')
    
    usuario = Usuario.objects.get(id=usuario_id)

    # Filtramos las preguntas según el tipo de usuario (OYM o LABORATORIO)
    preguntas = Pregunta.objects.filter(tipo_usuario=usuario.tipo_usuario)

    if request.method == 'POST':
        # El usuario envía sus respuestas
        tiempo_inicio = request.session.get('tiempo_inicio')
        tiempo_fin = time.time()
        duracion = int(tiempo_fin - tiempo_inicio) if tiempo_inicio else 0

        # Crear registro de examen
        examen = Examen.objects.create(usuario=usuario, fecha=timezone.now(), duracion=duracion)

        # Recorrer las preguntas para capturar la opción seleccionada
        for pregunta in preguntas:
            opcion_id_seleccionada = request.POST.get(str(pregunta.id))
            if opcion_id_seleccionada:
                opcion_obj = Opcion.objects.get(id=opcion_id_seleccionada)
                es_correcta = opcion_obj.es_correcta
                Respuesta.objects.create(
                    examen=examen,
                    pregunta=pregunta,
                    opcion=opcion_obj,
                    es_correcta=es_correcta
                )
        return redirect('resultado_examen', examen_id=examen.id)
    else:
        # Guardamos el tiempo de inicio en la sesión
        request.session['tiempo_inicio'] = time.time()

    return render(request, 'cuestionario/realizar_examen.html', {
        'preguntas': preguntas
    })

def resultado_examen(request, examen_id):
    # Mostramos resultados
    examen = Examen.objects.get(id=examen_id)
    respuestas = Respuesta.objects.filter(examen=examen)
    
    # Calculamos puntaje (ejemplo: 1 punto por respuesta correcta)
    puntaje = sum(resp.es_correcta for resp in respuestas)
    total_preguntas = respuestas.count()
    
    return render(request, 'cuestionario/resultado.html', {
        'examen': examen,
        'respuestas': respuestas,
        'puntaje': puntaje,
        'total_preguntas': total_preguntas
    })
