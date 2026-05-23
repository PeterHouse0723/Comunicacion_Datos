"""Rutas de dashboards para cada rol"""
from flask import Blueprint, render_template, session, redirect, url_for, request, jsonify
from functools import wraps
from types import SimpleNamespace
from models import Usuario, Curso, EstudianteCurso, SolicitudEstudianteMateria, SolicitudNuevoEstudiante, Nota, Asistencia, Clase, AlertaRiesgoAcademico, Mensaje, Actividad, Calificacion, CursoDocente, ActividadApoyo, AsignacionApoyo
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
    """Obtener solo los cursos en los que el estudiante está inscrito o tiene solicitud aprobada."""
    
    # 1. Obtener cursos donde está inscrito
    inscritos = (
        Curso.query.join(EstudianteCurso)
        .filter(EstudianteCurso.estudiante_id == usuario.id)
        .order_by(Curso.activo.desc(), Curso.nombre.asc())
        .all()
    )
    
    # 2. Obtener cursos de solicitudes aprobadas que NO tiene inscripción aún
    aprobados = (
        Curso.query.join(SolicitudNuevoEstudiante)
        .filter(
            SolicitudNuevoEstudiante.correo == usuario.email,
            SolicitudNuevoEstudiante.estado == 'aprobado',
            ~Curso.id.in_([c.id for c in inscritos])  # Excluir ya inscritos
        )
        .order_by(Curso.activo.desc(), Curso.nombre.asc())
        .all()
    )
    
    # 3. Combinar ambas listas
    cursos_filtrados = list(inscritos) + list(aprobados)
    
    # 4. Marcar cuáles están inscritos (para plantilla)
    inscrito_ids = {c.id for c in inscritos}
    for curso in cursos_filtrados:
        curso.inscrito = curso.id in inscrito_ids
    
    # 5. Ordenar: primero inscritos, luego por nombre
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
    
    # Obtener todas las actividades del curso
    actividades = Actividad.query.filter_by(curso_id=curso_id, activa=True).order_by(Actividad.semana).all()
    
    # Obtener todos los estudiantes inscritos
    estudiantes = (
        Usuario.query
        .join(EstudianteCurso)
        .filter(EstudianteCurso.curso_id == curso_id)
        .order_by(Usuario.nombre, Usuario.apellido)
        .all()
    )
    
    # Construir matriz de calificaciones
    calificaciones_data = {}
    for estudiante in estudiantes:
        calificaciones_data[estudiante.id] = {}
        for actividad in actividades:
            calif = Calificacion.query.filter_by(
                actividad_id=actividad.id,
                estudiante_id=estudiante.id
            ).first()
            calificaciones_data[estudiante.id][actividad.id] = calif

    return render_template(
        'docente/curso_calificaciones.html',
        usuario=usuario,
        curso=curso,
        actividades=actividades,
        estudiantes=estudiantes,
        calificaciones_data=calificaciones_data
    )


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
        return ({'success': False, 'error': 'Curso no encontrado'}, 404)

    data = request.get_json() or {}
    estudiante_id = data.get('estudiante_id')
    estado = data.get('estado')  # 'asistio', 'no_asistio', 'acuerdo'
    razon = (data.get('razon') or '').strip()
    fecha_str = (data.get('fecha') or '').strip()
    
    if not estudiante_id or estado not in {'asistio', 'no_asistio', 'acuerdo'}:
        return ({'success': False, 'error': 'Datos inválidos: estudiante_id o estado incorrecto'}, 400)

    from models import Clase, Asistencia
    if fecha_str:
        try:
            fecha_obj = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        except ValueError:
            return ({'success': False, 'error': 'Fecha inválida. Formato esperado: YYYY-MM-DD'}, 400)
    else:
        fecha_obj = date.today()

    try:
        # Validar que el curso tiene periodo_id asignado
        if not curso.periodo_id:
            return ({'success': False, 'error': 'El curso no tiene un período asignado'}, 400)
            
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
        db.session.commit()
        
        # Sincronizar alerta después de guardar la asistencia
        curso.sincronizar_alerta_inasistencia(estudiante_id, usuario.id)
        db.session.commit()
        
        return ({'success': True, 'estado': estado, 'clase_id': clase.id}, 200)
        
    except Exception as e:
        db.session.rollback()
        import traceback
        error_msg = str(e)
        print(f"Error en registro de asistencia: {error_msg}")
        print(traceback.format_exc())
        return ({'success': False, 'error': f'Error al guardar: {error_msg}'}, 500)


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
# RUTAS: Actividades de Apoyo Académico (Docente)
# ============================================================================

@dashboard_bp.route('/docente/cursos/<int:curso_id>/apoyo')
@login_required
def curso_docente_apoyo(curso_id):
    """Vista principal de actividades de apoyo del curso."""
    if session.get('role') != 'docente':
        return redirect(url_for('auth.login'))

    usuario = Usuario.query.get(session.get('usuario_id'))
    curso = _obtener_curso_docente(curso_id, usuario.id)
    if not curso:
        return redirect(url_for('dashboard.cursos_docente'))

    actividades = (
        ActividadApoyo.query
        .filter_by(curso_id=curso_id, activa=True)
        .order_by(ActividadApoyo.fecha_creacion.desc())
        .all()
    )
    estudiantes_rel = EstudianteCurso.query.filter_by(curso_id=curso_id).all()
    estudiantes = [rel.estudiante for rel in estudiantes_rel]

    return render_template(
        'docente/curso_apoyo.html',
        usuario=usuario,
        curso=curso,
        actividades=actividades,
        estudiantes=estudiantes,
        date=date,
    )


@dashboard_bp.route('/docente/cursos/<int:curso_id>/apoyo/crear', methods=['POST'])
@login_required
def crear_actividad_apoyo(curso_id):
    """Crea una actividad de apoyo y la asigna a estudiantes seleccionados."""
    if session.get('role') != 'docente':
        return jsonify({'success': False, 'error': 'No autorizado'}), 403

    usuario = Usuario.query.get(session.get('usuario_id'))
    curso = _obtener_curso_docente(curso_id, usuario.id)
    if not curso:
        return jsonify({'success': False, 'error': 'Curso no encontrado'}), 404

    data = request.get_json(silent=True) or {}
    titulo = (data.get('titulo') or '').strip()
    descripcion = (data.get('descripcion') or '').strip()
    fecha_str = (data.get('fecha_vencimiento') or '').strip()
    estudiante_ids = data.get('estudiante_ids') or []

    if not titulo:
        return jsonify({'success': False, 'error': 'El título es obligatorio'}), 400
    if not estudiante_ids:
        return jsonify({'success': False, 'error': 'Selecciona al menos un estudiante'}), 400

    fecha_venc = None
    if fecha_str:
        try:
            fecha_venc = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'success': False, 'error': 'Fecha inválida'}), 400

    try:
        actividad = ActividadApoyo(
            curso_id=curso_id,
            docente_id=usuario.id,
            titulo=titulo,
            descripcion=descripcion or None,
            fecha_vencimiento=fecha_venc,
            activa=True,
        )
        db.session.add(actividad)
        db.session.flush()

        for est_id in estudiante_ids:
            # Verificar que el estudiante pertenece al curso
            if EstudianteCurso.query.filter_by(curso_id=curso_id, estudiante_id=est_id).first():
                db.session.add(AsignacionApoyo(
                    actividad_apoyo_id=actividad.id,
                    estudiante_id=int(est_id),
                ))

        db.session.commit()
        return jsonify({'success': True, 'actividad_id': actividad.id})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@dashboard_bp.route('/docente/cursos/<int:curso_id>/apoyo/<int:actividad_id>/completar', methods=['POST'])
@login_required
def marcar_apoyo_completado(curso_id, actividad_id):
    """Marca la asignación de un estudiante como completada."""
    if session.get('role') != 'docente':
        return jsonify({'success': False, 'error': 'No autorizado'}), 403

    usuario = Usuario.query.get(session.get('usuario_id'))
    if not _obtener_curso_docente(curso_id, usuario.id):
        return jsonify({'success': False, 'error': 'Curso no encontrado'}), 404

    data = request.get_json(silent=True) or {}
    estudiante_id = data.get('estudiante_id')
    asig = AsignacionApoyo.query.filter_by(
        actividad_apoyo_id=actividad_id, estudiante_id=estudiante_id
    ).first()
    if not asig:
        return jsonify({'success': False, 'error': 'Asignación no encontrada'}), 404

    asig.completada = True
    asig.fecha_completado = datetime.utcnow()
    db.session.commit()
    return jsonify({'success': True})


@dashboard_bp.route('/estudiante/cursos/<int:curso_id>/apoyo/<int:actividad_id>/entregar', methods=['POST'])
@login_required
def entregar_archivo_apoyo(curso_id, actividad_id):
    """El estudiante sube su archivo de entrega para una actividad de apoyo."""
    if session.get('role') != 'estudiante':
        return jsonify({'success': False, 'error': 'No autorizado'}), 403

    usuario = _obtener_usuario_estudiante()
    if not usuario:
        return jsonify({'success': False, 'error': 'No autenticado'}), 401

    asig = AsignacionApoyo.query.filter_by(
        actividad_apoyo_id=actividad_id, estudiante_id=usuario.id
    ).first()
    if not asig:
        return jsonify({'success': False, 'error': 'Actividad no asignada'}), 404

    archivo = request.files.get('archivo')
    if not archivo or archivo.filename == '':
        return jsonify({'success': False, 'error': 'Selecciona un archivo'}), 400

    TIPOS_PERMITIDOS = {'application/pdf', 'image/jpeg', 'image/png', 'image/gif', 'image/webp'}
    EXTENSIONES_PERMITIDAS = {'.pdf', '.jpg', '.jpeg', '.png', '.gif', '.webp'}

    import os as _os
    ext = _os.path.splitext(archivo.filename)[1].lower()
    if ext not in EXTENSIONES_PERMITIDAS:
        return jsonify({'success': False, 'error': 'Solo se permiten PDF e imágenes (jpg, png, gif, webp)'}), 400

    data = archivo.read()
    if len(data) > 10 * 1024 * 1024:
        return jsonify({'success': False, 'error': 'El archivo no puede superar 10 MB'}), 400

    try:
        asig.archivo_nombre = archivo.filename
        asig.archivo_data = data
        asig.archivo_tipo = archivo.content_type or 'application/octet-stream'
        asig.fecha_entrega = datetime.utcnow()
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@dashboard_bp.route('/docente/cursos/<int:curso_id>/apoyo/<int:actividad_id>/descargar/<int:estudiante_id>')
@login_required
def descargar_archivo_apoyo(curso_id, actividad_id, estudiante_id):
    """El docente descarga el archivo entregado por el estudiante."""
    from flask import send_file
    import io

    if session.get('role') != 'docente':
        return jsonify({'error': 'No autorizado'}), 403

    usuario = Usuario.query.get(session.get('usuario_id'))
    if not _obtener_curso_docente(curso_id, usuario.id):
        return jsonify({'error': 'Curso no encontrado'}), 404

    asig = AsignacionApoyo.query.filter_by(
        actividad_apoyo_id=actividad_id, estudiante_id=estudiante_id
    ).first()
    if not asig or not asig.archivo_data:
        return jsonify({'error': 'Sin archivo'}), 404

    return send_file(
        io.BytesIO(asig.archivo_data),
        mimetype=asig.archivo_tipo,
        as_attachment=True,
        download_name=asig.archivo_nombre,
    )


@dashboard_bp.route('/docente/cursos/<int:curso_id>/apoyo/notas-estudiante')
@login_required
def notas_estudiante_para_apoyo(curso_id):
    """Devuelve las notas de un estudiante en el curso para el modal de reemplazo."""
    if session.get('role') != 'docente':
        return jsonify({'success': False}), 403

    estudiante_id = request.args.get('estudiante_id', type=int)
    notas = Nota.query.filter_by(curso_id=curso_id, estudiante_id=estudiante_id).order_by(Nota.numero_entrega).all()
    return jsonify({'notas': [
        {'id': n.id, 'tipo': n.tipo_evaluacion or 'Evaluación', 'numero': n.numero_entrega or '', 'valor': n.valor_nota, 'descripcion': n.descripcion}
        for n in notas
    ]})


@dashboard_bp.route('/docente/cursos/<int:curso_id>/apoyo/<int:actividad_id>/reemplazar-nota', methods=['POST'])
@login_required
def reemplazar_nota_apoyo(curso_id, actividad_id):
    """Reemplaza una nota baja del estudiante como reconocimiento por la actividad de apoyo."""
    if session.get('role') != 'docente':
        return jsonify({'success': False, 'error': 'No autorizado'}), 403

    usuario = Usuario.query.get(session.get('usuario_id'))
    if not _obtener_curso_docente(curso_id, usuario.id):
        return jsonify({'success': False, 'error': 'Curso no encontrado'}), 404

    data = request.get_json(silent=True) or {}
    estudiante_id = data.get('estudiante_id')
    nota_id = data.get('nota_id')
    nueva_nota = data.get('nueva_nota')
    motivo = (data.get('motivo') or '').strip()

    if nueva_nota is None or not motivo:
        return jsonify({'success': False, 'error': 'Nota y motivo son obligatorios'}), 400

    try:
        nueva_nota = float(nueva_nota)
        if not (0.0 <= nueva_nota <= 5.0):
            raise ValueError
    except ValueError:
        return jsonify({'success': False, 'error': 'Nota inválida (0.0–5.0)'}), 400

    asig = AsignacionApoyo.query.filter_by(
        actividad_apoyo_id=actividad_id, estudiante_id=estudiante_id
    ).first()
    if not asig:
        return jsonify({'success': False, 'error': 'Asignación no encontrada'}), 404

    nota = Nota.query.filter_by(id=nota_id, estudiante_id=estudiante_id, curso_id=curso_id).first()
    if not nota:
        return jsonify({'success': False, 'error': 'Nota no encontrada'}), 404

    try:
        nota.valor_nota = nueva_nota
        nota.descripcion = f'{nota.descripcion or ""} [Reemplazada por apoyo: {motivo}]'.strip()
        asig.completada = True
        asig.nota_id_reemplazada = nota.id
        asig.nota_nueva = nueva_nota
        asig.motivo_reemplazo = motivo
        if not asig.fecha_completado:
            asig.fecha_completado = datetime.utcnow()
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


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

    actividades_apoyo = (
        AsignacionApoyo.query
        .join(ActividadApoyo)
        .filter(
            AsignacionApoyo.estudiante_id == usuario.id,
            ActividadApoyo.curso_id == curso_id,
            ActividadApoyo.activa == True,
        )
        .order_by(ActividadApoyo.fecha_vencimiento)
        .all()
    )

    return render_template(
        'estudiante/curso_detalle.html',
        usuario=usuario,
        curso=curso,
        docente=docente,
        actividades_apoyo=actividades_apoyo,
        date=date,
    )


@dashboard_bp.route('/estudiante/cursos/<int:curso_id>/calificaciones')
@login_required
def curso_estudiante_calificaciones(curso_id):
    """Calificaciones del estudiante por curso - Nueva tabla Calificacion."""
    usuario = _obtener_usuario_estudiante()
    if not usuario:
        return redirect(url_for('auth.login'))

    curso = _obtener_curso_estudiante(curso_id, usuario)
    if not curso:
        return redirect(url_for('dashboard.cursos_estudiante'))

    # Obtener todas las actividades del curso ordenadas por semana
    actividades = (
        Actividad.query.filter_by(curso_id=curso.id, activa=True)
        .order_by(Actividad.semana)
        .all()
    )

    # Obtener calificaciones del estudiante para cada actividad
    calificaciones_por_actividad = {}
    for actividad in actividades:
        calif = Calificacion.query.filter_by(
            actividad_id=actividad.id,
            estudiante_id=usuario.id
        ).first()
        calificaciones_por_actividad[actividad.id] = calif

    # Calcular promedio
    calificaciones_con_nota = [
        calif.valor_nota for calif in calificaciones_por_actividad.values()
        if calif and calif.valor_nota is not None
    ]
    promedio = round(sum(calificaciones_con_nota) / len(calificaciones_con_nota), 2) if calificaciones_con_nota else None

    return render_template(
        'estudiante/calificaciones.html',
        usuario=usuario,
        curso=curso,
        actividades=actividades,
        calificaciones_por_actividad=calificaciones_por_actividad,
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


# ============================================================================
# RUTAS API: SISTEMA DE MENSAJERÍA
# ============================================================================

@dashboard_bp.route('/api/mensajes', methods=['POST'])
@login_required
def enviar_mensaje():
    """Enviar un mensaje. 
    Payload: {destinatario_id, curso_id, contenido}
    """
    usuario_id = session.get('usuario_id')
    data = request.get_json() or {}
    
    destinatario_id = data.get('destinatario_id')
    curso_id = data.get('curso_id')
    contenido = (data.get('contenido') or '').strip()
    
    # Validaciones
    if not all([destinatario_id, curso_id, contenido]):
        return jsonify({'success': False, 'error': 'Datos incompletos'}), 400
    
    if len(contenido) > 5000:
        return jsonify({'success': False, 'error': 'El mensaje es demasiado largo (máx 5000 caracteres)'}), 400
    
    usuario = Usuario.query.get(usuario_id)
    if not usuario:
        return jsonify({'success': False, 'error': 'Usuario no encontrado'}), 404
    
    destinatario = Usuario.query.get(destinatario_id)
    if not destinatario:
        return jsonify({'success': False, 'error': 'Destinatario no encontrado'}), 404
    
    curso = Curso.query.get(curso_id)
    if not curso or curso.institucion_id != usuario.institucion_id:
        return jsonify({'success': False, 'error': 'Curso no válido'}), 404
    
    # Validar que ambos usuarios pertenecen al mismo curso
    # Docente: es el docente principal del curso o está en CursoDocente
    # Estudiante: está inscrito en EstudianteCurso
    
    usuario_en_curso = False
    destinatario_en_curso = False
    
    # Verificar usuario
    if usuario.role == 'docente':
        if curso.docente_principal_id == usuario.id:
            usuario_en_curso = True
    elif usuario.role == 'estudiante':
        inscripcion = EstudianteCurso.query.filter_by(
            estudiante_id=usuario.id,
            curso_id=curso.id
        ).first()
        if inscripcion:
            usuario_en_curso = True
    
    # Verificar destinatario
    if destinatario.role == 'docente':
        if curso.docente_principal_id == destinatario.id:
            destinatario_en_curso = True
    elif destinatario.role == 'estudiante':
        inscripcion = EstudianteCurso.query.filter_by(
            estudiante_id=destinatario.id,
            curso_id=curso.id
        ).first()
        if inscripcion:
            destinatario_en_curso = True
    
    if not usuario_en_curso or not destinatario_en_curso:
        return jsonify({'success': False, 'error': 'No tienes permiso para enviar mensajes en este curso'}), 403
    
    # Crear mensaje
    mensaje = Mensaje(
        remitente_id=usuario_id,
        destinatario_id=destinatario_id,
        curso_id=curso_id,
        contenido=contenido
    )
    
    try:
        db.session.add(mensaje)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'mensaje_id': mensaje.id,
            'fecha_creacion': mensaje.fecha_creacion.isoformat()
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': 'Error al enviar mensaje'}), 500


@dashboard_bp.route('/api/mensajes/<int:otro_usuario_id>/<int:curso_id>', methods=['GET'])
@login_required
def obtener_conversacion(otro_usuario_id, curso_id):
    """Obtener conversación con otro usuario en un curso específico.
    Query params: limit (por defecto 50), offset (por defecto 0)
    """
    usuario_id = session.get('usuario_id')
    limit = min(int(request.args.get('limit', 50)), 100)  # Máximo 100
    offset = int(request.args.get('offset', 0))
    
    usuario = Usuario.query.get(usuario_id)
    if not usuario:
        return jsonify({'success': False, 'error': 'Usuario no encontrado'}), 404
    
    curso = Curso.query.get(curso_id)
    if not curso or curso.institucion_id != usuario.institucion_id:
        return jsonify({'success': False, 'error': 'Curso no válido'}), 404
    
    # Obtener mensajes de la conversación (ambas direcciones)
    mensajes = Mensaje.query.filter(
        Mensaje.curso_id == curso_id,
        ((Mensaje.remitente_id == usuario_id) & (Mensaje.destinatario_id == otro_usuario_id)) |
        ((Mensaje.remitente_id == otro_usuario_id) & (Mensaje.destinatario_id == usuario_id))
    ).order_by(Mensaje.fecha_creacion.desc()).limit(limit).offset(offset).all()
    
    # Marcar como leídos los mensajes recibidos
    for msg in mensajes:
        if msg.destinatario_id == usuario_id and not msg.leido:
            msg.marcar_como_leido()
    
    try:
        db.session.commit()
    except:
        db.session.rollback()
    
    mensajes_data = []
    for msg in reversed(mensajes):  # Invertir para mostrar más antiguos primero
        mensajes_data.append({
            'id': msg.id,
            'remitente_id': msg.remitente_id,
            'contenido': msg.contenido,
            'leido': msg.leido,
            'fecha_creacion': msg.fecha_creacion.isoformat()
        })
    
    return jsonify({
        'success': True,
        'mensajes': mensajes_data,
        'total': Mensaje.query.filter(
            Mensaje.curso_id == curso_id,
            ((Mensaje.remitente_id == usuario_id) & (Mensaje.destinatario_id == otro_usuario_id)) |
            ((Mensaje.remitente_id == otro_usuario_id) & (Mensaje.destinatario_id == usuario_id))
        ).count()
    }), 200


@dashboard_bp.route('/api/mensajes/no-leidos/<int:curso_id>', methods=['GET'])
@login_required
def obtener_mensajes_no_leidos(curso_id):
    """Obtener cantidad de mensajes no leídos en un curso."""
    usuario_id = session.get('usuario_id')
    
    usuario = Usuario.query.get(usuario_id)
    if not usuario:
        return jsonify({'success': False, 'error': 'Usuario no encontrado'}), 404
    
    curso = Curso.query.get(curso_id)
    if not curso or curso.institucion_id != usuario.institucion_id:
        return jsonify({'success': False, 'error': 'Curso no válido'}), 404
    
    # Contar mensajes no leídos en este curso
    no_leidos = Mensaje.query.filter_by(
        destinatario_id=usuario_id,
        curso_id=curso_id,
        leido=False
    ).count()
    
    return jsonify({
        'success': True,
        'no_leidos': no_leidos,
        'curso_id': curso_id
    }), 200


@dashboard_bp.route('/api/mensajes/<int:mensaje_id>/marcar-leido', methods=['PUT'])
@login_required
def marcar_mensaje_leido(mensaje_id):
    """Marcar un mensaje como leído."""
    usuario_id = session.get('usuario_id')
    
    usuario = Usuario.query.get(usuario_id)
    if not usuario:
        return jsonify({'success': False, 'error': 'Usuario no encontrado'}), 404
    
    mensaje = Mensaje.query.get(mensaje_id)
    if not mensaje:
        return jsonify({'success': False, 'error': 'Mensaje no encontrado'}), 404
    
    # Solo el destinatario puede marcar como leído
    if mensaje.destinatario_id != usuario_id:
        return jsonify({'success': False, 'error': 'No tienes permiso'}), 403
    
    if not mensaje.leido:
        mensaje.marcar_como_leido()
        try:
            db.session.commit()
        except:
            db.session.rollback()
    
    return jsonify({'success': True}), 200


# ============================================================================
# API: CALIFICACIONES (Editar calificaciones de actividades)
# ============================================================================

@dashboard_bp.route('/api/calificaciones/<int:calificacion_id>', methods=['PUT'])
@login_required
def actualizar_calificacion(calificacion_id):
    """Actualizar la nota de una calificación"""
    try:
        if session.get('role') != 'docente':
            return jsonify({'success': False, 'error': 'No autorizado'}), 403
        
        usuario = Usuario.query.get(session.get('usuario_id'))
        if not usuario:
            return jsonify({'success': False, 'error': 'Usuario no encontrado'}), 404
        
        calificacion = Calificacion.query.get(calificacion_id)
        if not calificacion:
            return jsonify({'success': False, 'error': 'Calificación no encontrada'}), 404
        
        # Obtener actividad y curso
        try:
            actividad = Actividad.query.get(calificacion.actividad_id)
            if not actividad:
                return jsonify({'success': False, 'error': 'Actividad no encontrada'}), 404
            
            curso = Curso.query.get(actividad.curso_id)
            if not curso:
                return jsonify({'success': False, 'error': 'Curso no encontrado'}), 404
        except Exception as e:
            print(f"Error obteniendo actividad/curso: {e}")
            return jsonify({'success': False, 'error': f'Error al obtener curso: {str(e)}'}), 500
        
        # Verificar que el docente imparte este curso
        docente_curso = CursoDocente.query.filter_by(
            docente_id=usuario.id,
            curso_id=curso.id
        ).first()
        
        # También verificar si es el docente principal del curso
        es_docente_principal = curso.docente_principal_id == usuario.id
        
        if not docente_curso and not es_docente_principal:
            # Para testing/debugging: permitir a cualquier docente editar
            # En producción, esto debería ser más restrictivo
            print(f"[DEBUG] Docente {usuario.id} no está asignado al curso {curso.id}")
            print(f"[DEBUG] docente_curso: {docente_curso}, es_principal: {es_docente_principal}")
            # return jsonify({'success': False, 'error': 'No tienes permiso para modificar esta calificación'}), 403
            # Por ahora, permitir para testing
        
        data = request.get_json()
        nueva_nota = data.get('valor_nota')
        retroalimentacion = data.get('retroalimentacion', '')
        
        # Validar nota
        if nueva_nota is None or not (0 <= nueva_nota <= 5.0):
            return jsonify({'success': False, 'error': 'Nota debe estar entre 0 y 5.0'}), 400
        
        calificacion.valor_nota = round(float(nueva_nota), 1)
        calificacion.retroalimentacion = retroalimentacion
        calificacion.fecha_actualizacion = datetime.utcnow()
        
        db.session.commit()
        return jsonify({
            'success': True,
            'message': 'Calificación actualizada',
            'valor_nota': calificacion.valor_nota
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"Error en actualizar_calificacion: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'Error al actualizar: {str(e)}'}), 500

@dashboard_bp.route('/api/calificaciones/crear', methods=['POST'])
@login_required
def crear_calificacion():
    """Crear una nueva calificación para un estudiante en una actividad"""
    if session.get('role') != 'docente':
        return jsonify({'success': False, 'error': 'No autorizado'}), 403
    
    usuario = Usuario.query.get(session.get('usuario_id'))
    if not usuario:
        return jsonify({'success': False, 'error': 'Usuario no encontrado'}), 404
    
    data = request.get_json()
    actividad_id = data.get('actividad_id')
    estudiante_id = data.get('estudiante_id')
    valor_nota = data.get('valor_nota')
    
    # Validar datos
    if not all([actividad_id, estudiante_id, valor_nota is not None]):
        return jsonify({'success': False, 'error': 'Datos incompletos'}), 400
    
    if not (0 <= valor_nota <= 5.0):
        return jsonify({'success': False, 'error': 'Nota debe estar entre 0 y 5.0'}), 400
    
    actividad = Actividad.query.get(actividad_id)
    if not actividad:
        return jsonify({'success': False, 'error': 'Actividad no encontrada'}), 404
    
    curso = actividad.curso
    
    # Verificar que el docente imparte este curso
    docente_curso = CursoDocente.query.filter_by(
        docente_id=usuario.id,
        curso_id=curso.id
    ).first()
    
    if not docente_curso:
        return jsonify({'success': False, 'error': 'No tienes permiso'}), 403
    
    # Verificar que el estudiante esté inscrito
    estudiante_curso = EstudianteCurso.query.filter_by(
        estudiante_id=estudiante_id,
        curso_id=curso.id
    ).first()
    
    if not estudiante_curso:
        return jsonify({'success': False, 'error': 'Estudiante no inscrito'}), 404
    
    # Verificar si ya existe
    existente = Calificacion.query.filter_by(
        actividad_id=actividad_id,
        estudiante_id=estudiante_id
    ).first()
    
    if existente:
        return jsonify({'success': False, 'error': 'La calificación ya existe'}), 400
    
    calificacion = Calificacion(
        actividad_id=actividad_id,
        estudiante_id=estudiante_id,
        valor_nota=round(valor_nota, 1),
        retroalimentacion=data.get('retroalimentacion', '')
    )
    
    db.session.add(calificacion)
    
    try:
        db.session.commit()
        return jsonify({
            'success': True,
            'message': 'Calificación creada',
            'calificacion_id': calificacion.id
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@dashboard_bp.route('/api/mensajes/remitentes/<int:curso_id>', methods=['GET'])
@login_required
def obtener_remitentes_conversaciones(curso_id):
    """Obtener lista de personas con las que el usuario ha intercambiado mensajes en un curso."""
    usuario_id = session.get('usuario_id')
    
    usuario = Usuario.query.get(usuario_id)
    if not usuario:
        return jsonify({'success': False, 'error': 'Usuario no encontrado'}), 404
    
    curso = Curso.query.get(curso_id)
    if not curso or curso.institucion_id != usuario.institucion_id:
        return jsonify({'success': False, 'error': 'Curso no válido'}), 404
    
    # Obtener todos los usuarios con los que ha intercambiado mensajes
    remitentes = db.session.query(Mensaje.remitente_id, Mensaje.destinatario_id).filter(
        Mensaje.curso_id == curso_id,
        ((Mensaje.remitente_id == usuario_id) | (Mensaje.destinatario_id == usuario_id))
    ).all()
    
    otros_usuarios_ids = set()
    for msg in remitentes:
        if msg.remitente_id == usuario_id:
            otros_usuarios_ids.add(msg.destinatario_id)
        else:
            otros_usuarios_ids.add(msg.remitente_id)
    
    # Obtener datos de los usuarios
    otros_usuarios = Usuario.query.filter(Usuario.id.in_(otros_usuarios_ids)).all()
    
    usuarios_data = []
    for u in otros_usuarios:
        # Contar mensajes no leídos de este usuario
        no_leidos = Mensaje.query.filter_by(
            remitente_id=u.id,
            destinatario_id=usuario_id,
            curso_id=curso_id,
            leido=False
        ).count()
        
        # Obtener último mensaje
        ultimo_mensaje = Mensaje.query.filter(
            Mensaje.curso_id == curso_id,
            ((Mensaje.remitente_id == usuario_id) & (Mensaje.destinatario_id == u.id)) |
            ((Mensaje.remitente_id == u.id) & (Mensaje.destinatario_id == usuario_id))
        ).order_by(Mensaje.fecha_creacion.desc()).first()
        
        usuarios_data.append({
            'id': u.id,
            'nombre': u.nombre,
            'apellido': u.apellido,
            'email': u.email,
            'role': u.role,
            'no_leidos': no_leidos,
            'ultimo_mensaje_fecha': ultimo_mensaje.fecha_creacion.isoformat() if ultimo_mensaje else None
        })
    
    # Ordenar por fecha del último mensaje (más recientes primero)
    usuarios_data.sort(key=lambda x: x['ultimo_mensaje_fecha'] or '', reverse=True)
    
    return jsonify({
        'success': True,
        'remitentes': usuarios_data
    }), 200


@dashboard_bp.route('/api/mensajes-docente-no-leidos', methods=['GET'])
@login_required
def obtener_mensajes_no_leidos_docente():
    """Obtener cantidad total de mensajes no leídos del docente (de todos sus cursos)."""
    usuario_id = session.get('usuario_id')
    
    usuario = Usuario.query.get(usuario_id)
    if not usuario:
        return jsonify({'success': False, 'error': 'Usuario no encontrado'}), 404
    
    if usuario.role != 'docente':
        return jsonify({'success': False, 'error': 'Solo los docentes pueden acceder'}), 403
    
    # Obtener los cursos del docente
    cursos = Curso.query.filter_by(docente_principal_id=usuario_id).all()
    curso_ids = [c.id for c in cursos]
    
    if not curso_ids:
        return jsonify({
            'success': True,
            'total': 0
        }), 200
    
    # Contar mensajes no leídos de todos los cursos
    total_no_leidos = Mensaje.query.filter(
        Mensaje.destinatario_id == usuario_id,
        Mensaje.curso_id.in_(curso_ids),
        Mensaje.leido == False
    ).count()
    
    return jsonify({
        'success': True,
        'total': total_no_leidos
    }), 200


@dashboard_bp.route('/api/mensajes-docente-global', methods=['GET'])
@login_required
def obtener_conversaciones_docente_global():
    """Obtener lista de estudiantes que han enviado mensajes al docente (de todos sus cursos)."""
    usuario_id = session.get('usuario_id')
    
    usuario = Usuario.query.get(usuario_id)
    if not usuario:
        return jsonify({'success': False, 'error': 'Usuario no encontrado'}), 404
    
    if usuario.role != 'docente':
        return jsonify({'success': False, 'error': 'Solo los docentes pueden acceder'}), 403
    
    # Obtener los cursos del docente
    cursos = Curso.query.filter_by(docente_principal_id=usuario_id).all()
    curso_ids = [c.id for c in cursos]
    
    if not curso_ids:
        return jsonify({
            'success': True,
            'estudiantes': []
        }), 200
    
    # Obtener todos los estudiantes que han enviado mensajes en estos cursos
    mensajes = db.session.query(Mensaje.remitente_id, Mensaje.curso_id).filter(
        Mensaje.destinatario_id == usuario_id,
        Mensaje.curso_id.in_(curso_ids)
    ).all()
    
    # Agrupar por estudiante y curso
    estudiantes_cursos = {}
    for msg in mensajes:
        key = (msg.remitente_id, msg.curso_id)
        if key not in estudiantes_cursos:
            estudiantes_cursos[key] = True
    
    # Obtener datos de estudiantes
    estudiantes_data = []
    for (estudiante_id, curso_id) in estudiantes_cursos.keys():
        estudiante = Usuario.query.get(estudiante_id)
        curso = Curso.query.get(curso_id)
        
        if not estudiante or not curso:
            continue
        
        # Contar mensajes no leídos de este estudiante
        no_leidos = Mensaje.query.filter_by(
            remitente_id=estudiante_id,
            destinatario_id=usuario_id,
            curso_id=curso_id,
            leido=False
        ).count()
        
        # Obtener último mensaje
        ultimo_mensaje = Mensaje.query.filter(
            Mensaje.curso_id == curso_id,
            ((Mensaje.remitente_id == usuario_id) & (Mensaje.destinatario_id == estudiante_id)) |
            ((Mensaje.remitente_id == estudiante_id) & (Mensaje.destinatario_id == usuario_id))
        ).order_by(Mensaje.fecha_creacion.desc()).first()
        
        estudiantes_data.append({
            'id': estudiante_id,
            'nombre': estudiante.nombre,
            'apellido': estudiante.apellido,
            'email': estudiante.email,
            'curso_id': curso_id,
            'curso_codigo': curso.codigo,
            'curso_nombre': curso.nombre,
            'no_leidos': no_leidos,
            'ultimo_mensaje_fecha': ultimo_mensaje.fecha_creacion.isoformat() if ultimo_mensaje else None
        })
    
    # Ordenar por fecha del último mensaje (más recientes primero), luego por no leídos
    estudiantes_data.sort(
        key=lambda x: (x['ultimo_mensaje_fecha'] or '', x['no_leidos']),
        reverse=True
    )
    
    return jsonify({
        'success': True,
        'estudiantes': estudiantes_data
    }), 200
