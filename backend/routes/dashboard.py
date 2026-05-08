"""Rutas de dashboards para cada rol"""
from flask import Blueprint, render_template, session, redirect, url_for, request
from functools import wraps
from types import SimpleNamespace
from models import Usuario, Curso, EstudianteCurso, SolicitudEstudianteMateria, Nota, Asistencia, Clase
from extensions import db
from datetime import datetime
from sqlalchemy import or_, func
from datetime import date

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')

# ============================================================================
# DECORADOR: Verificar sesión
# ============================================================================

def login_required(f):
    """Decorador para rutas que requieren autenticación"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

# ============================================================================
# RUTA: Dashboard Admin (redirige al nuevo admin.dashboard)
# ============================================================================

@dashboard_bp.route('/admin')
@login_required
def admin():
    """Redirige al nuevo panel administrativo"""
    if session.get('role') not in ['admin_global', 'admin_local']:
        return redirect(url_for('auth.login'))
    
    return redirect(url_for('admin.dashboard'))

# ============================================================================
# RUTA: Dashboard Docente
# ============================================================================

@dashboard_bp.route('/docente')
@login_required
def docente():
    """Dashboard para docentes"""
    if session.get('role') != 'docente':
        return redirect(url_for('auth.login'))
    
    usuario = Usuario.query.get(session.get('usuario_id'))
    materias = Curso.query.filter_by(docente_principal_id=usuario.id, activo=True).all()
    return render_template('docente/dashboard.html', usuario=usuario, materias=materias)

# ============================================================================
# RUTA: Cursos Docente
# ============================================================================

@dashboard_bp.route('/docente/cursosdocente')
@login_required
def cursos_docente():
    """Vista de cursos para docentes"""
    if session.get('role') != 'docente':
        return redirect(url_for('auth.login'))

    usuario = Usuario.query.get(session.get('usuario_id'))
    base_query = Curso.query.filter_by(docente_principal_id=usuario.id)
    query = base_query

    filtro = (request.args.get('filtro') or '').strip().lower()
    if filtro == 'activos':
        query = query.filter(Curso.activo.is_(True))
    elif filtro == 'inactivos':
        query = query.filter(Curso.activo.is_(False))

    buscar = (request.args.get('buscar') or '').strip()
    if buscar:
        like_term = f"%{buscar.lower()}%"
        query = query.filter(
            or_(
                func.lower(Curso.nombre).like(like_term),
                func.lower(Curso.codigo).like(like_term)
            )
        )

    ordenar = (request.args.get('ordenar') or 'nombre').strip().lower()
    if ordenar == 'codigo':
        query = query.order_by(Curso.codigo.asc())
    else:
        query = query.order_by(Curso.nombre.asc())

    vista = (request.args.get('vista') or 'tarjeta').strip().lower()
    if vista not in {'tarjeta', 'lista'}:
        vista = 'tarjeta'

    materias = query.all()
    materias_sugerencias = base_query.order_by(Curso.nombre.asc()).all()
    return render_template(
        'docente/cursosdocente.html',
        usuario=usuario,
        materias=materias,
        materias_sugerencias=materias_sugerencias,
        filtro=filtro,
        buscar=buscar,
        ordenar=ordenar,
        vista=vista
    )


def _obtener_curso_docente(curso_id, usuario_id):
    """Retorna el curso si pertenece al docente, si no devuelve None"""
    return Curso.query.filter_by(id=curso_id, docente_principal_id=usuario_id).first()


def _obtener_usuario_estudiante():
    """Retorna el usuario autenticado si existe y es estudiante."""
    if session.get('role') != 'estudiante':
        return None
    return Usuario.query.get(session.get('usuario_id'))


def _obtener_curso_estudiante(curso_id, usuario):
    """Retorna el curso si pertenece a la institución del estudiante."""
    return Curso.query.filter_by(id=curso_id, institucion_id=usuario.institucion_id).first()


def _obtener_cursos_estudiante(usuario):
    """Cursos cargados para la institución del estudiante, marcando cuáles están inscritos."""
    cursos = (
        Curso.query.filter_by(institucion_id=usuario.institucion_id)
        .order_by(Curso.activo.desc(), Curso.nombre.asc())
        .all()
    )
    inscritos_ids = {
        rel.curso_id
        for rel in EstudianteCurso.query.filter_by(estudiante_id=usuario.id).all()
    }

    for curso in cursos:
        curso.inscrito = curso.id in inscritos_ids

    cursos.sort(key=lambda curso: (not getattr(curso, 'inscrito', False), (curso.nombre or '').lower()))
    return cursos


@dashboard_bp.route('/docente/cursos/<int:curso_id>')
@login_required
def curso_docente_detalle(curso_id):
    """Detalle del curso para docente"""
    if session.get('role') != 'docente':
        return redirect(url_for('auth.login'))

    usuario = Usuario.query.get(session.get('usuario_id'))
    curso = _obtener_curso_docente(curso_id, usuario.id)
    if not curso:
        return redirect(url_for('dashboard.cursos_docente'))

    return render_template('docente/curso_detalle.html', usuario=usuario, curso=curso)


@dashboard_bp.route('/docente/cursos/<int:curso_id>/estudiantes')
@login_required
def curso_docente_estudiantes(curso_id):
    """Listado de estudiantes del curso para docente"""
    if session.get('role') != 'docente':
        return redirect(url_for('auth.login'))

    usuario = Usuario.query.get(session.get('usuario_id'))
    curso = _obtener_curso_docente(curso_id, usuario.id)
    if not curso:
        return redirect(url_for('dashboard.cursos_docente'))

    estudiantes_rel = EstudianteCurso.query.filter_by(curso_id=curso.id).all()
    estudiantes = [rel.estudiante for rel in estudiantes_rel]
    return render_template(
        'docente/curso_estudiantes.html',
        usuario=usuario,
        curso=curso,
        estudiantes=estudiantes
    )


@dashboard_bp.route('/docente/cursos/<int:curso_id>/calificaciones')
@login_required
def curso_docente_calificaciones(curso_id):
    """Vista de calificaciones del curso para docente"""
    if session.get('role') != 'docente':
        return redirect(url_for('auth.login'))

    usuario = Usuario.query.get(session.get('usuario_id'))
    curso = _obtener_curso_docente(curso_id, usuario.id)
    if not curso:
        return redirect(url_for('dashboard.cursos_docente'))

    return render_template('docente/curso_calificaciones.html', usuario=usuario, curso=curso)


@dashboard_bp.route('/docente/cursos/<int:curso_id>/asistencia')
@login_required
def curso_docente_asistencia(curso_id):
    """Vista de asistencia del curso para docente"""
    if session.get('role') != 'docente':
        return redirect(url_for('auth.login'))

    usuario = Usuario.query.get(session.get('usuario_id'))
    curso = _obtener_curso_docente(curso_id, usuario.id)
    if not curso:
        return redirect(url_for('dashboard.cursos_docente'))

    # Obtener estudiantes inscritos
    estudiantes_rel = EstudianteCurso.query.filter_by(curso_id=curso.id).all()
    estudiantes = [rel.estudiante for rel in estudiantes_rel]

    # Buscar si existe una clase para hoy
    hoy = date.today()
    clase_hoy = None
    from models import Clase, Asistencia
    clase_hoy = Clase.query.filter_by(curso_id=curso.id, fecha=hoy).first()

    asistencias_map = {}
    if clase_hoy:
        asistencias = Asistencia.query.filter_by(clase_id=clase_hoy.id).all()
        for a in asistencias:
            asistencias_map[a.estudiante_id] = a

    fecha_default = hoy.isoformat()
    return render_template('docente/curso_asistencia.html', usuario=usuario, curso=curso, estudiantes=estudiantes, clase_hoy=clase_hoy, asistencias_map=asistencias_map, fecha_default=fecha_default)


@dashboard_bp.route('/docente/cursos/<int:curso_id>/asistencia/registrar', methods=['POST'])
@login_required
def curso_docente_asistencia_registrar(curso_id):
    """Registrar o actualizar asistencia para un estudiante en una clase (crea clase para hoy si no existe)."""
    if session.get('role') != 'docente':
        return redirect(url_for('auth.login'))

    usuario = Usuario.query.get(session.get('usuario_id'))
    curso = _obtener_curso_docente(curso_id, usuario.id)
    if not curso:
        return ("Curso no encontrado", 404)

    data = request.get_json() or {}
    estudiante_id = data.get('estudiante_id')
    estado = data.get('estado')  # 'asistio', 'no_asistio', 'acuerdo'
    razon = (data.get('razon') or '').strip()
    if not estudiante_id or estado not in {'asistio', 'no_asistio', 'acuerdo'}:
        return ({'success': False, 'error': 'Datos inválidos'}, 400)

    from models import Clase, Asistencia
    hoy = date.today()
    clase = Clase.query.filter_by(curso_id=curso.id, fecha=hoy).first()
    if not clase:
        clase = Clase(curso_id=curso.id, periodo_id=curso.periodo_id, fecha=hoy)
        db.session.add(clase)
        db.session.flush()  # obtener id

    asistencia = Asistencia.query.filter_by(clase_id=clase.id, estudiante_id=estudiante_id).first()
    if not asistencia:
        asistencia = Asistencia(clase_id=clase.id, curso_id=curso.id, estudiante_id=estudiante_id)
        db.session.add(asistencia)

    if estado == 'asistio':
        asistencia.presente = True
        asistencia.justificacion = None
    elif estado == 'no_asistio':
        asistencia.presente = False
        asistencia.justificacion = razon if razon else None
    else:  # acuerdo
        asistencia.presente = False
        asistencia.justificacion = razon if razon else 'acuerdo'

    asistencia.fecha_registro = datetime.utcnow()
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return ({'success': False, 'error': 'Error al guardar'}, 500)

    return ({'success': True, 'estado': estado, 'clase_id': clase.id}, 200)


@dashboard_bp.route('/docente/cursos/<int:curso_id>/asistencia/por_fecha')
@login_required
def curso_docente_asistencia_por_fecha(curso_id):
    """Devuelve las asistencias para una fecha dada (query param `fecha` YYYY-MM-DD)."""
    if session.get('role') != 'docente':
        return redirect(url_for('auth.login'))

    usuario = Usuario.query.get(session.get('usuario_id'))
    curso = _obtener_curso_docente(curso_id, usuario.id)
    if not curso:
        return ({'success': False, 'error': 'Curso no encontrado'}, 404)

    fecha_str = request.args.get('fecha')
    try:
        if fecha_str:
            fecha_obj = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        else:
            fecha_obj = date.today()
    except Exception:
        return ({'success': False, 'error': 'Fecha inválida'}, 400)

    from models import Clase, Asistencia
    clase = Clase.query.filter_by(curso_id=curso.id, fecha=fecha_obj).first()
    if not clase:
        return ({'success': True, 'fecha': fecha_obj.isoformat(), 'clase_id': None, 'asistencias': [], 'descripcion': ''}, 200)

    asistencias = Asistencia.query.filter_by(clase_id=clase.id).all()
    lista = []
    for a in asistencias:
        estado = 'asistio' if a.presente else ('acuerdo' if a.justificacion == 'acuerdo' else 'no_asistio')
        lista.append({'estudiante_id': a.estudiante_id, 'estado': estado, 'justificacion': a.justificacion})

    descripcion = getattr(clase, 'tema', '') or ''
    return ({'success': True, 'fecha': fecha_obj.isoformat(), 'clase_id': clase.id, 'asistencias': lista, 'descripcion': descripcion}, 200)


@dashboard_bp.route('/docente/cursos/<int:curso_id>/asistencia/guardar', methods=['POST'])
@login_required
def curso_docente_asistencia_guardar(curso_id):
    """Guardar asistencia en lote para una fecha (crea clase si no existe). Payload: {fecha, descripcion, asistencias:[{estudiante_id, estado}]}
    """
    if session.get('role') != 'docente':
        return redirect(url_for('auth.login'))

    usuario = Usuario.query.get(session.get('usuario_id'))
    curso = _obtener_curso_docente(curso_id, usuario.id)
    if not curso:
        return ({'success': False, 'error': 'Curso no encontrado'}, 404)

    data = request.get_json() or {}
    fecha_str = data.get('fecha')
    descripcion = (data.get('descripcion') or '').strip()
    asistencias_list = data.get('asistencias') or []

    try:
        if fecha_str:
            fecha_obj = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        else:
            fecha_obj = date.today()
    except Exception:
        return ({'success': False, 'error': 'Fecha inválida'}, 400)

    from models import Clase, Asistencia
    clase = Clase.query.filter_by(curso_id=curso.id, fecha=fecha_obj).first()
    if not clase:
        clase = Clase(curso_id=curso.id, periodo_id=curso.periodo_id, fecha=fecha_obj)
        db.session.add(clase)
        db.session.flush()

    if descripcion:
        clase.tema = descripcion

    updated = 0
    for item in asistencias_list:
        estudiante_id = item.get('estudiante_id')
        estado = item.get('estado')
        if not estudiante_id or estado not in {'asistio', 'no_asistio', 'acuerdo'}:
            continue

        asistencia = Asistencia.query.filter_by(clase_id=clase.id, estudiante_id=estudiante_id).first()
        if not asistencia:
            asistencia = Asistencia(clase_id=clase.id, curso_id=curso.id, estudiante_id=estudiante_id)
            db.session.add(asistencia)

        if estado == 'asistio':
            asistencia.presente = True
            asistencia.justificacion = None
        elif estado == 'no_asistio':
            asistencia.presente = False
            asistencia.justificacion = None
        else:
            asistencia.presente = False
            asistencia.justificacion = 'acuerdo'

        asistencia.fecha_registro = datetime.utcnow()
        updated += 1

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return ({'success': False, 'error': 'Error al guardar en bloque'}, 500)

    return ({'success': True, 'updated': updated, 'clase_id': clase.id}, 200)


@dashboard_bp.route('/docente/cursos/<int:curso_id>/asistencia/fechas')
@login_required
def curso_docente_asistencia_fechas(curso_id):
    """Devuelve las fechas de clases (historial) para un curso."""
    if session.get('role') != 'docente':
        return redirect(url_for('auth.login'))

    usuario = Usuario.query.get(session.get('usuario_id'))
    curso = _obtener_curso_docente(curso_id, usuario.id)
    if not curso:
        return ({'success': False, 'error': 'Curso no encontrado'}, 404)

    from models import Clase
    clases = Clase.query.filter_by(curso_id=curso.id).order_by(Clase.fecha.desc()).all()
    lista = [{'id': c.id, 'fecha': c.fecha.isoformat(), 'descripcion': getattr(c, 'tema', '') or ''} for c in clases]
    return ({'success': True, 'fechas': lista}, 200)


@dashboard_bp.route('/docente/cursos/<int:curso_id>/asistencia/reset', methods=['POST'])
@login_required
def curso_docente_asistencia_reset(curso_id):
    """Elimina las asistencias registradas para una fecha (permite retomar). Payload: {fecha} (YYYY-MM-DD)"""
    if session.get('role') != 'docente':
        return redirect(url_for('auth.login'))

    usuario = Usuario.query.get(session.get('usuario_id'))
    curso = _obtener_curso_docente(curso_id, usuario.id)
    if not curso:
        return ({'success': False, 'error': 'Curso no encontrado'}, 404)

    data = request.get_json() or {}
    fecha_str = data.get('fecha')
    try:
        fecha_obj = datetime.strptime(fecha_str, '%Y-%m-%d').date()
    except Exception:
        return ({'success': False, 'error': 'Fecha inválida'}, 400)

    from models import Clase, Asistencia
    clase = Clase.query.filter_by(curso_id=curso.id, fecha=fecha_obj).first()
    if not clase:
        return ({'success': False, 'error': 'No existe clase para esa fecha'}, 404)

    try:
        Asistencia.query.filter_by(clase_id=clase.id).delete()
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return ({'success': False, 'error': 'Error al resetear asistencias'}, 500)

    return ({'success': True, 'message': 'Asistencias reiniciadas'}, 200)

# ============================================================================
# RUTA: SOLICITAR ESTUDIANTE A MATERIA (DOCENTE)
# ============================================================================

@dashboard_bp.route('/docente/solicitudes', methods=['POST'])
@login_required
def solicitar_estudiante_materia():
    """Crear solicitud para agregar estudiante a una materia"""
    if session.get('role') != 'docente':
        return jsonify({'success': False, 'error': 'No tienes permiso'}), 403

    data = request.get_json() or {}
    materia_id = data.get('materia_id')
    email = (data.get('email') or '').strip().lower()
    motivo = (data.get('motivo') or '').strip()

    if not materia_id or not email:
        return jsonify({'success': False, 'error': 'Materia y email requeridos'}), 400

    docente = Usuario.query.get(session.get('usuario_id'))
    materia = Curso.query.get(materia_id)
    if not materia or materia.docente_principal_id != docente.id:
        return jsonify({'success': False, 'error': 'Materia no válida'}), 404

    estudiante = Usuario.query.filter_by(email=email, role='estudiante').first()
    if not estudiante or estudiante.institucion_id != docente.institucion_id:
        return jsonify({'success': False, 'error': 'Estudiante no encontrado'}), 404

    inscrito = EstudianteCurso.query.filter_by(
        estudiante_id=estudiante.id,
        curso_id=materia.id
    ).first()
    if inscrito:
        return jsonify({'success': False, 'error': 'El estudiante ya está inscrito'}), 409

    existe = SolicitudEstudianteMateria.query.filter_by(
        curso_id=materia.id,
        estudiante_id=estudiante.id,
        docente_id=docente.id,
        estado='pendiente'
    ).first()
    if existe:
        return jsonify({'success': False, 'error': 'Ya existe una solicitud pendiente'}), 409

    solicitud = SolicitudEstudianteMateria(
        curso_id=materia.id,
        estudiante_id=estudiante.id,
        docente_id=docente.id,
        motivo=motivo
    )

    db.session.add(solicitud)
    db.session.commit()

    return jsonify({'success': True, 'mensaje': 'Solicitud enviada'}), 201

# ============================================================================
# RUTA: Dashboard Estudiante
# ============================================================================

@dashboard_bp.route('/estudiante')
@login_required
def estudiante():
    """Dashboard para estudiantes"""
    if session.get('role') != 'estudiante':
        return redirect(url_for('auth.login'))
    
    usuario = Usuario.query.get(session.get('usuario_id'))
    return render_template('estudiante/dashboard.html', usuario=usuario)


@dashboard_bp.route('/estudiante/dashboard')
@login_required
def dashboard_estudiante():
    """Alias para volver al dashboard del estudiante."""
    return estudiante()


@dashboard_bp.route('/estudiante/cursos')
@login_required
def cursos_estudiante():
    """Lista los cursos cargados para la institución del estudiante y marca cuáles están inscritos."""
    usuario = _obtener_usuario_estudiante()
    if not usuario:
        return redirect(url_for('auth.login'))

    cursos = _obtener_cursos_estudiante(usuario)
    return render_template('estudiante/cursos.html', usuario=usuario, cursos=cursos)


@dashboard_bp.route('/estudiante/cursos/<int:curso_id>')
@login_required
def curso_estudiante_detalle(curso_id):
    """Detalle de un curso para el estudiante."""
    usuario = _obtener_usuario_estudiante()
    if not usuario:
        return redirect(url_for('auth.login'))

    curso = _obtener_curso_estudiante(curso_id, usuario)
    if not curso:
        return redirect(url_for('dashboard.cursos_estudiante'))

    docente = curso.docente_principal
    curso.semestre = curso.periodo.nombre if getattr(curso, 'periodo', None) else None
    return render_template('estudiante/curso_detalle.html', usuario=usuario, curso=curso, docente=docente)


@dashboard_bp.route('/estudiante/cursos/<int:curso_id>/calificaciones')
@login_required
def curso_estudiante_calificaciones(curso_id):
    """Calificaciones del estudiante por curso."""
    usuario = _obtener_usuario_estudiante()
    if not usuario:
        return redirect(url_for('auth.login'))

    curso = _obtener_curso_estudiante(curso_id, usuario)
    if not curso:
        return redirect(url_for('dashboard.cursos_estudiante'))

    notas = (
        Nota.query.filter_by(estudiante_id=usuario.id, curso_id=curso.id)
        .order_by(Nota.fecha_registro.desc())
        .all()
    )
    calificaciones = [
        {
            'nombre': nota.descripcion or f'Evaluación {index}',
            'tipo': nota.tipo_evaluacion or 'Desconocido',
            'calificacion': nota.valor_nota,
            'fecha_registro': nota.fecha_registro,
        }
        for index, nota in enumerate(notas, start=1)
    ]
    promedio = round(sum(nota.valor_nota for nota in notas) / len(notas), 2) if notas else None
    return render_template(
        'estudiante/calificaciones.html',
        usuario=usuario,
        curso=curso,
        calificaciones=calificaciones,
        promedio=promedio,
    )


@dashboard_bp.route('/estudiante/cursos/<int:curso_id>/asistencia')
@login_required
def curso_estudiante_asistencia(curso_id):
    """Asistencia del estudiante por curso."""
    usuario = _obtener_usuario_estudiante()
    if not usuario:
        return redirect(url_for('auth.login'))

    curso = _obtener_curso_estudiante(curso_id, usuario)
    if not curso:
        return redirect(url_for('dashboard.cursos_estudiante'))

    asistencias_db = (
        Asistencia.query.filter_by(estudiante_id=usuario.id, curso_id=curso.id)
        .order_by(Asistencia.fecha_registro.desc())
        .all()
    )

    asistencias = []
    conteo = SimpleNamespace(presente=0, ausente=0, justificada=0)
    for asistencia in asistencias_db:
        clase = asistencia.clase
        tema = clase.tema if clase else None
        fecha = clase.fecha if clase else asistencia.fecha_registro

        if asistencia.presente:
            conteo.presente += 1
        elif asistencia.justificacion == 'acuerdo' or asistencia.justificacion:
            conteo.justificada += 1
        else:
            conteo.ausente += 1

        asistencias.append({
            'fecha': fecha,
            'presente': asistencia.presente,
            'justificacion': asistencia.justificacion,
            'tema': tema,
        })

    return render_template(
        'estudiante/asistencia.html',
        usuario=usuario,
        curso=curso,
        asistencias=asistencias,
        asistencias_count=conteo,
    )
