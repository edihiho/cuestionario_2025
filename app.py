import os
import sys
import shutil
import time
import random
from flask import (
    Flask, render_template, request, redirect, url_for, flash,
    session, send_file, jsonify, Response
)
from config.database import create_tables, crear_admins, get_connection
from controllers.auth_controller import AuthController
from controllers.pregunta_controller import PreguntaController
from controllers.estadisticas_controller import EstadisticasController
from utils.app_config import load_app_config, save_app_config
from utils.file_loader import FileLoader
import pandas as pd

# Forzar la inclusión de la carpeta raíz del proyecto en sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

app = Flask(__name__, template_folder='templates')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'tu_clave_secreta')  # Cambia esto en producción

# Integración con WhiteNoise para servir archivos estáticos
from whitenoise import WhiteNoise
app.wsgi_app = WhiteNoise(app.wsgi_app, root=os.path.join(project_root, 'static/'), prefix='static/')

# Configuración para la base de datos: Si se define DATABASE_URL, se usará Postgres
if os.getenv('DATABASE_URL'):
    print("Usando Postgres desde la variable de entorno DATABASE_URL.")
    # Asegúrate de que config/database.py utilice DATABASE_URL para conectarse a Postgres.
else:
    print("No se encontró DATABASE_URL; se usará la base de datos por defecto (SQLite u otra configurada).")

def crear_examen(usuario_id):
    """
    Inserta un examen y retorna su ID (usando RETURNING id para Postgres).
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO examenes (usuario_id) VALUES (%s) RETURNING id", 
            (usuario_id,)
        )
        exam_id = cursor.fetchone()[0]
        conn.commit()
        return exam_id
    except Exception as e:
        print("Error al crear examen:", e)
        conn.rollback()
        return None
    finally:
        conn.close()

def actualizar_duracion_examen(examen_id, duracion):
    """
    Actualiza la duración del examen.
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE examenes SET duracion = %s WHERE id = %s", 
            (duracion, examen_id)
        )
        conn.commit()
    except Exception as e:
        print("Error al actualizar duración:", e)
        conn.rollback()
    finally:
        conn.close()

def create_app():
    # Crear las tablas y administradores (asegúrate de que estas funciones sean compatibles con Postgres)
    create_tables()
    crear_admins()

    # RUTA RAÍZ
    @app.route('/')
    def index():
        return redirect(url_for('login'))

    # LOGIN
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            correo = request.form.get('correo')
            contraseña = request.form.get('contraseña')
            if not correo or not contraseña:
                flash("Por favor, ingrese su correo y contraseña.", "error")
                return redirect(url_for('login'))
            usuario = AuthController.login(correo, contraseña)
            if usuario:
                session['usuario'] = {
                    'id': usuario.id,
                    'nombre': usuario.nombre,
                    'rol': usuario.rol,
                    'tipo_usuario': usuario.tipo_usuario
                }
                flash(f"✅ Inicio de sesión exitoso: {usuario.nombre} ({usuario.tipo_usuario})", "success")
                if usuario.rol == 'admin':
                    return redirect(url_for('admin_dashboard'))
                else:
                    return redirect(url_for('examen_view'))
            else:
                flash("❌ Credenciales incorrectas.", "error")
                return redirect(url_for('login'))
        return render_template('login.html')

    # LOGOUT
    @app.route('/logout')
    def logout():
        session.clear()
        flash("Sesión finalizada.", "info")
        return redirect(url_for('login'))

    # DASHBOARD ADMIN
    @app.route('/admin/dashboard')
    def admin_dashboard():
        usuario = session.get('usuario')
        if not usuario or usuario.get('rol') != 'admin':
            flash("Acceso denegado.", "error")
            return redirect(url_for('login'))
        config_data = load_app_config()
        usuarios = AuthController.listar_usuarios(usuario.get('tipo_usuario'))
        examenes = EstadisticasController.obtener_examenes_por_tipo(usuario.get('tipo_usuario'))
        active_tab = request.args.get('active_tab', 'usuarios')
        return render_template(
            'admin_dashboard.html',
            usuario=usuario,
            config_data=config_data,
            usuarios=usuarios,
            preguntas=PreguntaController.obtener_preguntas_completas_por_tipo(usuario.get('tipo_usuario')),
            examenes=examenes,
            active_tab=active_tab
        )
    
    # GUARDAR PARÁMETROS DEL EXAMEN
    @app.route('/admin/config/guardar', methods=['POST'])
    def guardar_parametros_examen():
        usuario = session.get('usuario')
        if not usuario or usuario.get('rol') != 'admin':
            return redirect(url_for('login'))
        try:
            num_preguntas = request.form.get('num_preguntas')
            tiempo_limite = request.form.get('tiempo_limite')
            config_data = load_app_config()
            config_data.setdefault("exam_params", {})
            config_data["exam_params"]["num_preguntas"] = int(num_preguntas)
            config_data["exam_params"]["tiempo_limite"] = int(tiempo_limite)
            save_app_config(config_data)
            flash(f"Parámetros guardados: {num_preguntas} preguntas, {tiempo_limite} minutos", "success")
        except Exception as e:
            flash(f"Error al guardar parámetros: {e}", "error")
        return redirect(url_for('admin_dashboard', active_tab='config'))

    # RESPALDAR BD (Descargar Backup)
    @app.route('/admin/config/respaldo')
    def respaldar_bd():
        try:
            db_path = os.path.join(project_root, "examenes.db")
            backup_path = os.path.join(project_root, "examenes_backup.db")
            if not os.path.exists(db_path):
                flash("No se encontró la base de datos.", "error")
                return redirect(url_for('admin_dashboard', active_tab='config'))
            shutil.copy(db_path, backup_path)
            flash("Base de datos respaldada correctamente.", "success")
            return send_file(backup_path, as_attachment=True)
        except Exception as e:
            flash(f"Error al respaldar la BD: {e}", "error")
            return redirect(url_for('admin_dashboard', active_tab='config'))

    # RESTAURAR BD (Subir Backup)
    @app.route('/admin/config/restaurar', methods=['POST'])
    def restaurar_bd():
        try:
            backup_file = request.files.get('backup_file')
            if not backup_file:
                flash("No se seleccionó ningún archivo.", "error")
                return redirect(url_for('admin_dashboard', active_tab='config'))
            backup_path = os.path.join(project_root, "examenes_backup_uploaded.db")
            backup_file.save(backup_path)
            db_path = os.path.join(project_root, "examenes.db")
            shutil.copy(backup_path, db_path)
            flash("Base de datos restaurada correctamente.", "success")
        except Exception as e:
            flash(f"Error al restaurar la BD: {e}", "error")
        return redirect(url_for('admin_dashboard', active_tab='config'))

    # APLICAR TEMA
    @app.route('/admin/config/aplicar_tema', methods=['POST'])
    def aplicar_tema():
        try:
            tema = request.form.get('tema')
            config_data = load_app_config()
            config_data['tema'] = tema
            save_app_config(config_data)
            flash(f"Tema aplicado: {tema}", "success")
        except Exception as e:
            flash(f"Error al aplicar el tema: {e}", "error")
        return redirect(url_for('admin_dashboard', active_tab='config'))

    # ABRIR LOGS
    @app.route('/admin/config/abrir_logs')
    def abrir_logs():
        try:
            log_path = os.path.join(project_root, "app.log")
            if not os.path.exists(log_path):
                with open(log_path, "w", encoding="utf-8") as f:
                    f.write("Registro de actividad:\n")
            with open(log_path, "r", encoding="utf-8") as f:
                logs = f.read()
            flash("Registros abiertos. Revisa la consola o descarga el archivo.", "info")
        except Exception as e:
            flash(f"Error al abrir los logs: {e}", "error")
        return redirect(url_for('admin_dashboard', active_tab='config'))

    # GUARDAR NOTIFICACIONES
    @app.route('/admin/config/guardar_notificaciones', methods=['POST'])
    def guardar_notificaciones():
        try:
            habilitado = request.form.get('notificaciones') == 'on'
            correo = request.form.get('correo_notif')
            config_data = load_app_config()
            config_data.setdefault('notificaciones', {})
            config_data['notificaciones']['habilitado'] = habilitado
            config_data['notificaciones']['correo'] = correo
            save_app_config(config_data)
            flash("Notificaciones guardadas.", "success")
        except Exception as e:
            flash(f"Error al guardar notificaciones: {e}", "error")
        return redirect(url_for('admin_dashboard', active_tab='config'))

    # SINCRONIZAR PREGUNTAS
    @app.route('/admin/config/sincronizar_preguntas')
    def sincronizar_preguntas():
        flash("Preguntas sincronizadas correctamente.", "success")
        return redirect(url_for('admin_dashboard', active_tab='config'))

    # GESTIÓN DE USUARIOS
    @app.route('/admin/users', methods=['GET', 'POST'])
    def admin_users():
        usuario = session.get('usuario')
        if not usuario or usuario.get('rol') != 'admin':
            return redirect(url_for('login'))
        if request.method == 'POST':
            nombre = request.form.get('nombre')
            correo = request.form.get('correo')
            contraseña = request.form.get('contraseña')
            rol = request.form.get('rol')
            localidad = request.form.get('localidad')
            if AuthController.registrar_usuario(nombre, correo, contraseña, usuario.get('tipo_usuario'), rol, localidad):
                flash("Usuario creado correctamente.", "success")
            else:
                flash("No se pudo crear el usuario.", "error")
            return redirect(url_for('admin_users'))
        usuarios = AuthController.listar_usuarios(usuario.get('tipo_usuario'))
        return render_template('admin_users.html', tipo_usuario=usuario.get('tipo_usuario'), usuarios=usuarios)

    @app.route('/admin/users/eliminar', methods=['POST'])
    def eliminar_usuario():
        usuario = session.get('usuario')
        if not usuario or usuario.get('rol') != 'admin':
            return redirect(url_for('login'))
        usuario_id = request.form.get('usuario_id')
        if usuario_id and AuthController.eliminar_usuario(int(usuario_id)):
            flash("Usuario eliminado correctamente.", "success")
        else:
            flash("No se pudo eliminar el usuario.", "error")
        return redirect(url_for('admin_users'))

    # GESTIÓN DE PREGUNTAS
    @app.route('/admin/questions', methods=['GET'])
    def admin_questions():
        usuario = session.get('usuario')
        if not usuario or usuario.get('rol') != 'admin':
            return redirect(url_for('login'))
        preguntas = PreguntaController.obtener_preguntas_completas_por_tipo(usuario.get('tipo_usuario'))
        return render_template('admin_questions.html', tipo_usuario=usuario.get('tipo_usuario'), preguntas=preguntas)

    @app.route('/admin/questions/eliminar', methods=['POST'])
    def eliminar_pregunta():
        usuario = session.get('usuario')
        if not usuario or usuario.get('rol') != 'admin':
            return redirect(url_for('login'))
        pregunta_id = request.form.get('pregunta_id')
        if pregunta_id and PreguntaController.eliminar_pregunta(int(pregunta_id)):
            flash("Pregunta eliminada correctamente.", "success")
        else:
            flash("No se pudo eliminar la pregunta.", "error")
        return redirect(url_for('admin_questions'))

    # CARGAR PREGUNTAS DESDE EXCEL
    @app.route('/admin/cargar_excel', methods=['GET', 'POST'])
    def cargar_excel():
        usuario = session.get('usuario')
        if not usuario or usuario.get('rol') != 'admin':
            return redirect(url_for('login'))
        if request.method == 'POST':
            excel_file = request.files.get('excel_file')
            if excel_file:
                temp_path = os.path.join(project_root, "temp_excel_file.xlsx")
                excel_file.save(temp_path)
                if FileLoader.cargar_preguntas_desde_excel(temp_path, usuario.get('tipo_usuario')):
                    flash("Preguntas cargadas correctamente.", "success")
                else:
                    flash("No se pudieron cargar las preguntas.", "error")
                os.remove(temp_path)
            else:
                flash("Debe seleccionar un archivo.", "error")
            return redirect(url_for('admin_questions'))
        return render_template('cargar_excel.html')

    # EXPORTAR ESTADÍSTICAS A EXCEL (pendiente de implementar detalles)
    @app.route('/admin/exportar_excel')
    def exportar_excel():
        usuario = session.get('usuario')
        if not usuario or usuario.get('rol') != 'admin':
            return redirect(url_for('login'))
        flash("Exportación a Excel pendiente de implementación.", "info")
        return redirect(url_for('admin_statistics'))

    # AGREGAR PREGUNTA (Formulario)
    @app.route('/admin/pregunta_form', methods=['GET', 'POST'])
    def pregunta_form():
        usuario = session.get('usuario')
        if not usuario or usuario.get('rol') != 'admin':
            return redirect(url_for('login'))
        if request.method == 'POST':
            pregunta = request.form.get('pregunta')
            categoria = request.form.get('categoria')
            if not pregunta:
                flash("La pregunta no puede estar vacía.", "error")
                return redirect(url_for('pregunta_form'))
            if PreguntaController.agregar_pregunta(pregunta, categoria, usuario.get('tipo_usuario')):
                flash("Pregunta agregada correctamente.", "success")
                return redirect(url_for('admin_questions'))
            else:
                flash("No se pudo agregar la pregunta.", "error")
        return render_template('pregunta_form.html')

    # ESTADÍSTICAS ADMIN
    @app.route('/admin/statistics')
    def admin_statistics():
        usuario = session.get('usuario')
        if not usuario or usuario.get('rol') != 'admin':
            return redirect(url_for('login'))
        examenes = EstadisticasController.obtener_examenes_por_tipo(usuario.get('tipo_usuario'))
        return render_template('admin_statistics.html', examenes=examenes)

    @app.route('/admin/cargar_estadisticas')
    def cargar_estadisticas():
        usuario = session.get('usuario')
        if not usuario or usuario.get('rol') != 'admin':
            return redirect(url_for('login'))
        examenes = EstadisticasController.obtener_examenes_por_tipo(usuario.get('tipo_usuario'))
        return render_template('admin_statistics.html', examenes=examenes)

    # Rutas para gráficas (funcionalidad pendiente)
    @app.route('/admin/grafica/duracion_correctas')
    def grafica_duracion_correctas():
        flash("Funcionalidad de gráfica pendiente.", "info")
        return redirect(url_for('admin_statistics'))

    @app.route('/admin/grafica/top_usuarios')
    def grafica_top_usuarios():
        flash("Funcionalidad de gráfica pendiente.", "info")
        return redirect(url_for('admin_statistics'))

    @app.route('/admin/grafica/preguntas_falladas')
    def grafica_preguntas_falladas():
        flash("Funcionalidad de gráfica pendiente.", "info")
        return redirect(url_for('admin_statistics'))

    @app.route('/admin/grafica/top_incorrectas')
    def grafica_top_incorrectas():
        flash("Funcionalidad de gráfica pendiente.", "info")
        return redirect(url_for('admin_statistics'))
    
    # CAMBIAR CONTRASEÑA
    @app.route('/admin/cambiar_contraseña/<int:user_id>', methods=['GET', 'POST'])
    def cambiar_contraseña(user_id):
        usuario = session.get('usuario')
        if not usuario:
            flash("Debe iniciar sesión.", "error")
            return redirect(url_for('login'))
        if usuario['rol'] != 'admin' and usuario['id'] != user_id:
            flash("Acceso denegado.", "error")
            return redirect(url_for('login'))
        if request.method == 'POST':
            nueva_contraseña = request.form.get('nueva_contraseña')
            confirmar_contraseña = request.form.get('confirmar_contraseña')
            if not nueva_contraseña or not confirmar_contraseña:
                flash("Por favor, complete ambos campos.", "error")
                return redirect(url_for('cambiar_contraseña', user_id=user_id))
            if nueva_contraseña != confirmar_contraseña:
                flash("Las contraseñas no coinciden.", "error")
                return redirect(url_for('cambiar_contraseña', user_id=user_id))
            if len(nueva_contraseña) < 6:
                flash("La contraseña debe tener al menos 6 caracteres.", "error")
                return redirect(url_for('cambiar_contraseña', user_id=user_id))
            if AuthController.cambiar_contrasena(user_id, nueva_contraseña):
                return redirect(url_for('admin_users'))
            else:
                flash("Error al actualizar la contraseña.", "error")
                return redirect(url_for('cambiar_contraseña', user_id=user_id))
        return render_template('cambiar_contrasena.html', user_id=user_id)

    # EXAMEN PARA USUARIOS NO ADMIN
    @app.route('/examen', methods=['GET', 'POST'])
    def examen_view():
        usuario = session.get('usuario')
        if not usuario:
            flash("Debe iniciar sesión.", "error")
            return redirect(url_for('login'))
        config_data = load_app_config()
        if request.method == 'GET':
            if 'examen_id' not in session or 'preguntas_examen' not in session:
                examen_id = crear_examen(usuario['id'])
                if examen_id is None:
                    flash("Error al crear el examen.", "error")
                    return redirect(url_for('examen_view'))
                session['examen_id'] = examen_id
                session['examen_start'] = time.time()
                all_preguntas = PreguntaController.obtener_preguntas_completas_por_tipo(usuario.get('tipo_usuario'))
                random.shuffle(all_preguntas)
                max_preguntas = config_data.get('exam_params', {}).get('num_preguntas', len(all_preguntas))
                session['preguntas_examen'] = all_preguntas[:max_preguntas]
            preguntas = session.get('preguntas_examen', [])
            return render_template('examen_view.html', usuario=usuario, preguntas=preguntas, config_data=config_data)
        else:
            examen_id = session.get('examen_id')
            if not examen_id:
                flash("No se encontró el examen en sesión.", "error")
                return redirect(url_for('examen_view'))
            examen_start = session.get('examen_start')
            duration = int(time.time() - examen_start) if examen_start else 0
            actualizar_duracion_examen(examen_id, duration)
            preguntas = session.get('preguntas_examen', [])
            for pregunta in preguntas:
                opcion_id = request.form.get(f"respuesta_{pregunta['id']}")
                if opcion_id:
                    PreguntaController.guardar_respuesta(examen_id, pregunta['id'], opcion_id)
            flash("Respuestas enviadas correctamente.", "success")
            session.pop('examen_id', None)
            session.pop('examen_start', None)
            session.pop('preguntas_examen', None)
            return redirect(url_for('resultados_view', exam_id=examen_id))

    # RESULTADOS Y ESTADÍSTICAS DEL EXAMEN ACTUAL
    @app.route('/resultados/<int:exam_id>')
    def resultados_view(exam_id):
        stats = EstadisticasController.obtener_estadisticas_examen(exam_id)
        return render_template('resultados_view.html', exam_id=exam_id, stats=stats)

    # GRÁFICA DE CALIFICACIÓN (adaptada para Postgres)
    @app.route('/admin/grafica/calificacion')
    def grafica_calificacion():
        usuarios_str = request.args.get('usuario', '').strip()
        lista_usuarios = [u.strip() for u in usuarios_str.split(',') if u.strip()] if usuarios_str else []
        fecha_inicio = request.args.get('fecha_inicio', '').strip()
        fecha_fin = request.args.get('fecha_fin', '').strip()
        localidad = request.args.get('localidad', '').strip()
        conn = get_connection()
        cursor = conn.cursor()
        query = """
            SELECT e.id AS exam_id,
                   u.nombre,
                   to_char(e.fecha, 'YYYY-MM-DD HH24:MI:SS') AS fecha,
                   (SELECT COUNT(*) FROM respuestas r 
                      JOIN opciones o ON r.opcion_id = o.id
                      WHERE r.examen_id = e.id AND o.es_correcta = true) AS correctas,
                   (SELECT COUNT(*) FROM respuestas r 
                      JOIN opciones o ON r.opcion_id = o.id
                      WHERE r.examen_id = e.id) AS total_respuestas
            FROM examenes e
            JOIN usuarios u ON e.usuario_id = u.id
            WHERE 1=1
        """
        params = []
        if lista_usuarios:
            placeholders = ",".join(["%s"] * len(lista_usuarios))
            query += f" AND u.nombre IN ({placeholders})"
            params.extend(lista_usuarios)
        if localidad:
            query += " AND u.localidad = %s"
            params.append(localidad)
        if fecha_inicio:
            query += " AND date(e.fecha) >= %s"
            params.append(fecha_inicio)
        if fecha_fin:
            query += " AND date(e.fecha) <= %s"
            params.append(fecha_fin)
        query += " ORDER BY e.fecha DESC"
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        labels = []
        calificaciones = []
        for row in rows:
            total = row["total_respuestas"]
            correct = row["correctas"]
            grade = round((correct / total) * 10, 2) if total > 0 else 0.0
            labels.append(f"Examen {row['exam_id']} - {row['nombre']} - {row['fecha']}")
            calificaciones.append(grade)
        data = {
            "labels": labels,
            "calificaciones": calificaciones
        }
        return jsonify(data)

    # EXPORTAR ESTADÍSTICAS A EXCEL (Calificación)
    @app.route('/admin/exportar_excel_calificacion')
    def exportar_excel_calificacion():
        usuario = session.get('usuario')
        if not usuario or usuario.get('rol') != 'admin':
            flash("Acceso denegado.", "error")
            return redirect(url_for('login'))
        filtro_usuarios = request.args.get('usuario', '')
        filtro_fecha_inicio = request.args.get('fecha_inicio', '')
        filtro_fecha_fin = request.args.get('fecha_fin', '')
        conn = get_connection()
        cursor = conn.cursor()
        query = """
            SELECT u.nombre, u.localidad, e.id AS exam_id, 
                   to_char(e.fecha, 'YYYY-MM-DD HH24:MI:SS') AS fecha,
                   e.duracion,
                   (SELECT COUNT(*) FROM respuestas r 
                      JOIN opciones o ON r.opcion_id = o.id
                      WHERE r.examen_id = e.id AND o.es_correcta = true) AS correctas,
                   (SELECT COUNT(*) FROM respuestas r 
                      JOIN opciones o ON r.opcion_id = o.id
                      WHERE r.examen_id = e.id AND o.es_correcta = false) AS incorrectas
            FROM examenes e
            JOIN usuarios u ON e.usuario_id = u.id
            WHERE u.rol = 'usuario'
        """
        params = []
        if filtro_usuarios:
            usuarios_lista = [u.strip() for u in filtro_usuarios.split(',') if u.strip()]
            if usuarios_lista:
                placeholders = ",".join(["%s"] * len(usuarios_lista))
                query += f" AND u.nombre IN ({placeholders})"
                params.extend(usuarios_lista)
        if filtro_fecha_inicio and filtro_fecha_fin:
            query += " AND e.fecha BETWEEN %s AND %s"
            params.extend([filtro_fecha_inicio, filtro_fecha_fin])
        query += " ORDER BY e.fecha DESC"
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        data = []
        for row in rows:
            total_preguntas = row["correctas"] + row["incorrectas"]
            nota_final = round((row["correctas"] / total_preguntas * 10) if total_preguntas > 0 else 0, 2)
            porcentaje = round((row["correctas"] / total_preguntas * 100) if total_preguntas > 0 else 0, 2)
            data.append({
                "Usuario": row["nombre"],
                "Localidad": row["localidad"],
                "Examen ID": row["exam_id"],
                "Fecha": row["fecha"],
                "Duración (s)": row["duracion"],
                "Correctas": row["correctas"],
                "Incorrectas": row["incorrectas"],
                "Nota Final": nota_final,
                "Porcentaje": porcentaje
            })
        df = pd.DataFrame(data)
        temp_dir = os.path.join(project_root, "temp")
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)
        file_path = os.path.join(temp_dir, "estadisticas.xlsx")
        with pd.ExcelWriter(file_path, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, sheet_name="Estadísticas")
        return send_file(
            file_path,
            as_attachment=True,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            download_name="estadisticas.xlsx"
        )

    # GRÁFICA: TOP INCORRECTAS POR PREGUNTA
    @app.route('/admin/grafica/top_incorrectas_preguntas')
    def grafica_top_incorrectas_preguntas():
        fecha_inicio = request.args.get('fecha_inicio', '').strip()
        fecha_fin = request.args.get('fecha_fin', '').strip()
        conn = get_connection()
        cursor = conn.cursor()
        query = """
            SELECT p.pregunta, COUNT(r.id) AS incorrectas
            FROM preguntas p
            LEFT JOIN respuestas r ON p.id = r.pregunta_id
            LEFT JOIN examenes e ON r.examen_id = e.id
            LEFT JOIN usuarios u ON e.usuario_id = u.id
            WHERE u.rol = 'usuario'
        """
        params = []
        if fecha_inicio:
            query += " AND date(e.fecha) >= %s"
            params.append(fecha_inicio)
        if fecha_fin:
            query += " AND date(e.fecha) <= %s"
            params.append(fecha_fin)
        query += " GROUP BY p.id ORDER BY incorrectas DESC LIMIT 10"
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        labels = [row["pregunta"] for row in rows]
        incorrect_counts = [row["incorrectas"] for row in rows]
        return jsonify({
            "labels": labels,
            "incorrect_counts": incorrect_counts
        })

    return app

# Crear la aplicación (nivel global para que Gunicorn la encuentre)
app = create_app()

if __name__ == '__main__':
    env = os.getenv('FLASK_ENV', 'production').lower()
    if env == 'development':
        host = os.getenv('FLASK_RUN_HOST', '127.0.0.1')
        port = int(os.getenv('FLASK_RUN_PORT', 5000))
        debug = True
    else:
        host = os.getenv('FLASK_RUN_HOST', '0.0.0.0')
        port = int(os.getenv('FLASK_RUN_PORT', 8000))
        debug = False
    app.run(host=host, port=port, debug=debug)
