"""Rutas de dashboards para cada rol"""
from flask import Blueprint, render_template, session, redirect, url_for, request, jsonify
from functools import wraps
from types import SimpleNamespace
from models import Usuario, Curso, EstudianteCurso, SolicitudEstudianteMateria, SolicitudNuevoEstudiante, Nota, Asistencia, Clase, AlertaRiesgoAcademico
from extensions import db
from datetime import datetime, timedelta
from sqlalchemy import or_, func
from datetime import date
from utils import validar_email

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


@dashboard_bp.route('/docente/alertas')
@login_required
def alertas_docente():
    """Listado de materias del docente con alertas de asistencia."""
    if session.get('role') != 'docente':
        return redirect(url_for('auth.login'))

    usuario = Usuario.query.get(session.get('usuario_id'))
    materias = _obtener_cursos_docente(usuario)
    total_estudiantes_en_riesgo = 0

    for materia in materias:
        riesgos = _obtener_estudiantes_en_riesgo(materia)
        materia.riesgos_count = len(riesgos)
        materia.riesgos_activos = riesgos
        total_estudiantes_en_riesgo += len(riesgos)

    materias_con_riesgo = sum(1 for materia in materias if getattr(materia, 'riesgos_count', 0) > 0)

    return render_template(
        'docente/alertas.html',
        usuario=usuario,
        materias=materias,
        materias_con_riesgo=materias_con_riesgo,
        total_estudiantes_en_riesgo=total_estudiantes_en_riesgo,
    )


@dashboard_bp.route('/docente/alertas/<int:curso_id>')
@login_required
def alerta_docente_detalle(curso_id):
    """Detalle de alertas por materia para docentes."""
    if session.get('role') != 'docente':
        return redirect(url_for('auth.login'))

    usuario = Usuario.query.get(session.get('usuario_id'))
    curso = _obtener_curso_docente(curso_id, usuario.id)
    if not curso:
        return redirect(url_for('dashboard.alertas_docente'))

    estudiantes_rel = EstudianteCurso.query.filter_by(curso_id=curso.id).all()
    riesgos = _obtener_estudiantes_en_riesgo(curso)

    return render_template(
        'docente/alerta_detalle.html',
        usuario=usuario,
        curso=curso,
        estudiantes_total=len(estudiantes_rel),
        riesgos=riesgos,
        riesgos_total=len(riesgos),
    )

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
    """Retorna el curso SOLO si el estudiante está inscrito en él."""
    # Verificar que existe una inscripción del estudiante en este curso
    inscripcion = EstudianteCurso.query.filter_by(
        estudiante_id=usuario.id,
        curso_id=curso_id
    ).first()
    
    if not inscripcion:
        return None  # No está inscrito
    
    # Obtener el curso si existe y pertenece a su institución
    return Curso.query.filter_by(
        id=curso_id,
        institucion_id=usuario.institucion_id
    ).first()


def _obtener_cursos_estudiante(usuario):
    """Cursos cargados para la institución del estudiante, marcando cuáles están inscritos.
    Excluye cursos con SOLO solicitudes rechazadas (sin inscripción ni aprobadas)."""
    cursos = (
        Curso.query.filter_by(institucion_id=usuario.institucion_id)
        .order_by(Curso.activo.desc(), Curso.nombre.asc())
        .all()
    )
    
    # Obtener IDs de cursos con inscripciones
    inscritos_ids = {
        rel.curso_id
        for rel in EstudianteCurso.query.filter_by(estudiante_id=usuario.id).all()
    }
    
    # Obtener IDs de cursos donde hay solicitudes aprobadas
    aprobados_ids = {
        sol.curso_id
        for sol in SolicitudNuevoEstudiante.query.filter(
            SolicitudNuevoEstudiante.correo == usuario.email,
            SolicitudNuevoEstudiante.estado == 'aprobado'
        ).all()
    }
    
    # Obtener IDs de cursos donde hay solicitudes rechazadas
    rechazados_ids = {
        sol.curso_id
        for sol in SolicitudNuevoEstudiante.query.filter(
            SolicitudNuevoEstudiante.correo == usuario.email,
            SolicitudNuevoEstudiante.estado == 'rechazado'
        ).all()
    }
    
    # Filtrar cursos: excluir SOLO si están rechazados Y sin inscripción Y sin aprobación
    cursos_filtrados = [
        curso for curso in cursos 
        if not (curso.id in rechazados_ids and 
                curso.id not in inscritos_ids and 
                curso.id not in aprobados_ids)
    ]
    
    # Marcar cuáles están inscritos
    for curso in cursos_filtrados:
        curso.inscrito = curso.id in inscritos_ids

    cursos_filtrados.sort(key=lambda curso: (not getattr(curso, 'inscrito', False), (curso.nombre or '').lower()))
    return cursos_filtrados


def _calcular_racha_inasistencias(curso_id, estudiante_id):
    """Calcula la racha actual de inasistencias consecutivas del estudiante en un curso."""
    asistencias = (
        Asistencia.query.join(Clase)
        .filter(
            Asistencia.curso_id == curso_id,
            Asistencia.estudiante_id == estudiante_id,
        )
        .order_by(Clase.fecha.desc(), Clase.id.desc())
        .all()
    )

    racha = 0
    ultima_fecha = None
    for asistencia in asistencias:
        ultima_fecha = asistencia.clase.fecha if asistencia.clase else ultima_fecha
        if asistencia.presente:
            break
        racha += 1

    return racha, ultima_fecha


def _resumen_riesgo_docente(curso, estudiante):
    """Construye el resumen de riesgo por asistencia para un estudiante."""
    resumen = curso.resumen_asistencia_estudiante(estudiante.id)
    racha_inasistencias, ultima_fecha = _calcular_racha_inasistencias(curso.id, estudiante.id)

    alerta_activa = AlertaRiesgoAcademico.query.filter_by(
        estudiante_id=estudiante.id,
        curso_id=curso.id,
        tipo_alerta='inasistencia',
        estado='activa'
    ).first()

    porcentaje_inasistencia = resumen['porcentaje_inasistencia']
    razones = []

    if alerta_activa:
        razones.append(alerta_activa.descripcion or 'Alerta activa de inasistencia.')
    elif porcentaje_inasistencia >= 35.0:
        razones.append(f'Inasistencia acumulada del {porcentaje_inasistencia}%')

    if racha_inasistencias > 2:
        razones.append(f'{racha_inasistencias} inasistencias seguidas')

    if not razones:
        return None

    return {
        'estudiante': estudiante,
        'resumen': resumen,
        'alerta_activa': alerta_activa,
        'porcentaje_inasistencia': porcentaje_inasistencia,
        'racha_inasistencias': racha_inasistencias,
        'ultima_fecha': ultima_fecha,
        'razones': razones,
        'es_riesgo_critico': racha_inasistencias > 2 or porcentaje_inasistencia >= 35.0,
    }


def _obtener_estudiantes_en_riesgo(curso):
    """Devuelve los estudiantes del curso que están en riesgo por inasistencia."""
    estudiantes_rel = EstudianteCurso.query.filter_by(curso_id=curso.id).all()
    riesgos = []

    for rel in estudiantes_rel:
        info = _resumen_riesgo_docente(curso, rel.estudiante)
        if info:
            riesgos.append(info)

    riesgos.sort(
        key=lambda item: (
            item['es_riesgo_critico'],
            item['racha_inasistencias'],
            item['porcentaje_inasistencia'],
            (item['estudiante'].apellido or '').lower(),
            (item['estudiante'].nombre or '').lower(),
        ),
        reverse=True,
    )
    return riesgos


def _obtener_cursos_docente(usuario):
    """Cursos asignados al docente."""
    return (
        Curso.query.filter_by(docente_principal_id=usuario.id)
        .order_by(Curso.activo.desc(), Curso.nombre.asc())
        .all()
    )


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
    """Registrar o actualizar asistencia para un estudiante en una clase (crea clase para la fecha seleccionada si no existe)."""
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
    fecha_str = (data.get('fecha') or '').strip()
    if not estudiante_id or estado not in {'asistio', 'no_asistio', 'acuerdo'}:
        return ({'success': False, 'error': 'Datos inválidos'}, 400)

    from models import Clase, Asistencia
    if fecha_str:
        try:
            fecha_obj = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        except ValueError:
            return ({'success': False, 'error': 'Fecha inválida'}, 400)
    else:
        fecha_obj = date.today()

    clase = Clase.query.filter_by(curso_id=curso.id, fecha=fecha_obj).first()
    if not clase:
        # Si el curso tiene dias_semana definidos, solo permitir crear clase si la fecha seleccionada es uno de esos días
        dias_definidos = curso.get_dias_semana_list() if hasattr(curso, 'get_dias_semana_list') else []
        if dias_definidos and fecha_obj.weekday() not in dias_definidos:
            return ({'success': False, 'error': 'La fecha seleccionada no corresponde a un día de clase programado para este curso'}, 400)

        clase = Clase(curso_id=curso.id, periodo_id=curso.periodo_id, fecha=fecha_obj)
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

    try:
        curso.sincronizar_alerta_inasistencia(estudiante_id, usuario.id)
        db.session.commit()
    except Exception:
        db.session.rollback()

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
    """Guardar asistencia en lote para una fecha (crea clase si no existe). Payload: {fecha, descripcion, asistencias:[{estudiante_id, estado, justificacion}]}
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
        dias_definidos = curso.get_dias_semana_list() if hasattr(curso, 'get_dias_semana_list') else []
        if dias_definidos and fecha_obj.weekday() not in dias_definidos:
            return ({'success': False, 'error': 'La fecha indicada no corresponde a un día de clase programado para este curso'}, 400)

        clase = Clase(curso_id=curso.id, periodo_id=curso.periodo_id, fecha=fecha_obj)
        db.session.add(clase)
        db.session.flush()

    if descripcion:
        clase.tema = descripcion

    updated = 0
    for item in asistencias_list:
        estudiante_id = item.get('estudiante_id')
        estado = item.get('estado')
        justificacion = (item.get('justificacion') or '').strip()
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
            asistencia.justificacion = justificacion if justificacion else None
        else:  # acuerdo
            asistencia.presente = False
            asistencia.justificacion = justificacion if justificacion else 'acuerdo'

        asistencia.fecha_registro = datetime.utcnow()
        updated += 1

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return ({'success': False, 'error': 'Error al guardar en bloque'}, 500)

    try:
        for item in asistencias_list:
            estudiante_id = item.get('estudiante_id')
            if estudiante_id:
                curso.sincronizar_alerta_inasistencia(estudiante_id, usuario.id)
        db.session.commit()
    except Exception:
        db.session.rollback()

    return ({'success': True, 'updated': updated, 'clase_id': clase.id}, 200)


@dashboard_bp.route('/docente/cursos/<int:curso_id>/asistencia/fechas')
@login_required
def curso_docente_asistencia_fechas(curso_id):
    """Devuelve el calendario de clases programadas para un curso con su estado."""
    if session.get('role') != 'docente':
        return redirect(url_for('auth.login'))

    usuario = Usuario.query.get(session.get('usuario_id'))
    curso = _obtener_curso_docente(curso_id, usuario.id)
    if not curso:
        return ({'success': False, 'error': 'Curso no encontrado'}, 404)

    dias_definidos = curso.get_dias_semana_list() if hasattr(curso, 'get_dias_semana_list') else []
    if not dias_definidos or not curso.periodo:
        return ({'success': False, 'error': 'Este curso no tiene días de clase configurados'}, 400)

    from models import Clase, Asistencia
    clases = Clase.query.filter_by(curso_id=curso.id).all()
    clases_por_fecha = {c.fecha: c for c in clases}
    hoy = date.today()

    calendario = []
    current = curso.periodo.fecha_inicio
    while current <= curso.periodo.fecha_fin:
        if current.weekday() in dias_definidos:
            clase = clases_por_fecha.get(current)
            asistencias_count = 0
            if clase:
                asistencias_count = Asistencia.query.filter_by(clase_id=clase.id).count()

            if current > hoy:
                estado = 'pendiente'
            elif clase and asistencias_count > 0:
                estado = 'tomada'
            else:
                estado = 'sin_tomar'

            calendario.append({
                'fecha': current.isoformat(),
                'dia': current.day,
                'mes': current.month,
                'anio': current.year,
                'estado': estado,
                'clase_id': clase.id if clase else None,
                'descripcion': getattr(clase, 'tema', '') or '',
            })
        current = current + timedelta(days=1)

    calendario.sort(key=lambda item: item['fecha'])
    return ({'success': True, 'calendario': calendario, 'dias_programados': dias_definidos}, 200)


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
# RUTA: Solicitar Nuevo Estudiante (DOCENTE)
# ============================================================================

@dashboard_bp.route('/docente/solicitar-estudiante')
@login_required
def solicitar_nuevo_estudiante():
    """Formulario para que docente solicite agregar un estudiante nuevo"""
    if session.get('role') != 'docente':
        return redirect(url_for('auth.login'))
    
    usuario = Usuario.query.get(session.get('usuario_id'))
    cursos = Curso.query.filter_by(docente_principal_id=usuario.id, activo=True).all()
    
    return render_template('docente/solicitar_nuevo_estudiante.html', usuario=usuario, cursos=cursos)


@dashboard_bp.route('/docente/solicitar-estudiante', methods=['POST'])
@login_required
def crear_solicitud_nuevo_estudiante():
    """Crear solicitud de nuevo estudiante"""
    if session.get('role') != 'docente':
        return jsonify({'success': False, 'error': 'No autorizado'}), 403
    
    try:
        data = request.get_json()
        docente = Usuario.query.get(session.get('usuario_id'))
        
        nombre = data.get('nombre', '').strip()
        apellido = data.get('apellido', '').strip()
        correo = data.get('correo', '').strip()
        curso_id = data.get('curso_id')
        
        # Validaciones
        if not all([nombre, apellido, correo, curso_id]):
            return jsonify({'success': False, 'error': 'Campos requeridos vacíos'}), 400
        
        if not validar_email(correo):
            return jsonify({'success': False, 'error': 'Correo inválido'}), 400
        
        # Verificar que el curso pertenece al docente
        curso = Curso.query.get(curso_id)
        if not curso or curso.docente_principal_id != docente.id:
            return jsonify({'success': False, 'error': 'Curso no válido'}), 404
        
        # Verificar que no exista solicitud pendiente/aprobada para este correo y curso
        existe_solicitud = SolicitudNuevoEstudiante.query.filter(
            SolicitudNuevoEstudiante.correo == correo,
            SolicitudNuevoEstudiante.curso_id == curso_id,
            SolicitudNuevoEstudiante.estado.in_(['pendiente', 'aprobado'])
        ).first()
        if existe_solicitud:
            return jsonify({'success': False, 'error': 'Ya existe una solicitud pendiente o aprobada para este correo en este curso'}), 409
        
        # Si el usuario existe, verificar que NO esté inscrito en este curso
        existe_usuario = Usuario.query.filter_by(email=correo).first()
        if existe_usuario:
            # Verificar si ya está inscrito en este curso
            inscripcion = EstudianteCurso.query.filter_by(
                estudiante_id=existe_usuario.id,
                curso_id=curso_id
            ).first()
            if inscripcion:
                return jsonify({'success': False, 'error': 'Este estudiante ya está inscrito en este curso'}), 409
        
        # Crear solicitud
        solicitud = SolicitudNuevoEstudiante(
            curso_id=curso_id,
            docente_id=docente.id,
            nombre=nombre,
            apellido=apellido,
            correo=correo
        )
        
        db.session.add(solicitud)
        db.session.commit()
        
        return jsonify({'success': True, 'mensaje': 'Solicitud enviada al administrador', 'id': solicitud.id}), 201
        
    except Exception as e:
        db.session.rollback()
        print(f"[ERROR] Error al crear solicitud: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@dashboard_bp.route('/docente/mis-solicitudes')
@login_required
def mis_solicitudes_docente():
    """Ver solicitudes de nuevo estudiantes enviadas por el docente"""
    if session.get('role') != 'docente':
        return redirect(url_for('auth.login'))
    
    usuario = Usuario.query.get(session.get('usuario_id'))
    
    # Obtener solicitudes con paginación
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    solicitudes = SolicitudNuevoEstudiante.query.filter_by(docente_id=usuario.id).order_by(
        SolicitudNuevoEstudiante.fecha_solicitud.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template(
        'docente/mis_solicitudes.html',
        usuario=usuario,
        solicitudes=solicitudes.items,
        page=page,
        total_pages=solicitudes.pages,
        total=solicitudes.total
    )

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
    alertas_query = (
        AlertaRiesgoAcademico.query.join(Curso)
        .filter(
            AlertaRiesgoAcademico.estudiante_id == usuario.id,
            Curso.institucion_id == usuario.institucion_id
        )
    )
    alertas_activas_count = alertas_query.filter(AlertaRiesgoAcademico.estado == 'activa').count()
    alertas_totales_count = alertas_query.count()

    return render_template(
        'estudiante/dashboard.html',
        usuario=usuario,
        alertas_activas_count=alertas_activas_count,
        alertas_totales_count=alertas_totales_count,
    )


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


@dashboard_bp.route('/estudiante/alertas')
@login_required
def alertas_estudiante():
    """Listar alertas académicas del estudiante."""
    usuario = _obtener_usuario_estudiante()
    if not usuario:
        return redirect(url_for('auth.login'))

    alertas = (
        AlertaRiesgoAcademico.query.join(Curso)
        .filter(
            AlertaRiesgoAcademico.estudiante_id == usuario.id,
            Curso.institucion_id == usuario.institucion_id
        )
        .order_by(AlertaRiesgoAcademico.fecha_alerta.desc())
        .all()
    )

    alertas_activas = [alerta for alerta in alertas if alerta.estado == 'activa']
    return render_template(
        'estudiante/alertas.html',
        usuario=usuario,
        alertas=alertas,
        alertas_activas=alertas_activas,
        total_alertas=len(alertas),
    )


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

    resumen = curso.resumen_asistencia_estudiante(usuario.id)

    asistencias_db = (
        Asistencia.query.filter_by(estudiante_id=usuario.id, curso_id=curso.id)
        .order_by(Asistencia.fecha_registro.desc())
        .all()
    )

    asistencias = []
    conteo = SimpleNamespace(
        presente=resumen['presentes'],
        ausente=resumen['ausentes'],
        justificada=resumen['justificadas']
    )
    for asistencia in asistencias_db:
        clase = asistencia.clase
        tema = clase.tema if clase else None
        fecha = clase.fecha if clase else asistencia.fecha_registro

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
        resumen_asistencia=resumen,
    )
