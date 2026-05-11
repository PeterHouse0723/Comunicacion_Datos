"""Rutas administrativas - Admin Global"""
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session
from extensions import db
from models import Usuario, Institucion, Curso, Periodo, CursoDocente, EstudianteCurso, SolicitudEstudianteMateria
from utils import validar_email, validar_contraseña, encriptar_contraseña, verificar_contraseña
from functools import wraps
from datetime import datetime
import csv
import io
import math

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# ============================================================================
# DECORADOR: Verificar si es admin
# ============================================================================

def admin_required(f):
    """Decorador para rutas que requieren ser admin"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session:
            if request.is_json:
                return jsonify({'success': False, 'error': 'Sesion expirada'}), 401
            return redirect(url_for('auth.login'))
        
        # Obtener usuario actual
        usuario = Usuario.query.get(session['usuario_id'])
        if not usuario or usuario.role not in ['admin_global', 'admin_local']:
            if request.is_json:
                return jsonify({'success': False, 'error': 'No tienes permiso'}), 403
            return redirect(url_for('auth.login'))
        
        return f(*args, **kwargs)
    return decorated_function

# ============================================================================
# RUTA: DASHBOARD PRINCIPAL
# ============================================================================

@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    """Panel principal del admin"""
    usuario = Usuario.query.get(session['usuario_id'])

    if usuario.role == 'admin_global':
        pendientes = Usuario.query.filter_by(role='admin_local', estado='pendiente').count()
        instituciones_count = Institucion.query.filter_by(activo=True).count()
        cursos_count = Curso.query.filter_by(activo=True).count()
        admins_locales_count = Usuario.query.filter_by(role='admin_local').count()

        stats = {
            'docentes_pendientes': pendientes,
            'instituciones': instituciones_count,
            'cursos': cursos_count,
            'usuarios': admins_locales_count
        }
    else:
        docentes_pendientes = Usuario.query.filter_by(
            role='docente',
            estado='pendiente',
            institucion_id=usuario.institucion_id
        ).count()
        cursos_count = Curso.query.filter_by(
            institucion_id=usuario.institucion_id,
            activo=True
        ).count()
        usuarios_count = Usuario.query.filter_by(
            institucion_id=usuario.institucion_id,
            role='docente'
        ).count()

        stats = {
            'docentes_pendientes': docentes_pendientes,
            'cursos': cursos_count,
            'usuarios': usuarios_count
        }
    
    if usuario.role == 'admin_local':
        return render_template('admin_local/dashboard.html', stats=stats, usuario=usuario)

    return render_template('admin/dashboard.html', stats=stats, usuario=usuario)

# ============================================================================
# RUTA: LISTADO DE DOCENTES PENDIENTES
# ============================================================================

@admin_bp.route('/docentes/pendientes')
@admin_required
def docentes_pendientes():
    """Listar docentes pendientes de aprobación con paginación"""
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    usuario = Usuario.query.get(session['usuario_id'])

    if usuario.role == 'admin_global':
        return redirect(url_for('admin.dashboard'))
    
    # Si es admin_local, solo ver su institución
    if usuario.role == 'admin_local':
        query = Usuario.query.filter_by(role='docente', estado='pendiente', 
                                        institucion_id=usuario.institucion_id)
    else:
        # admin_global ve todos
        query = Usuario.query.filter_by(role='docente', estado='pendiente')
    
    total = query.count()
    docentes = query.paginate(page=page, per_page=per_page, error_out=False).items
    
    total_pages = math.ceil(total / per_page)
    
    template_name = 'admin/docentes_pendientes.html'
    if usuario.role == 'admin_local':
        template_name = 'admin_local/docentes_pendientes.html'

    return render_template(template_name,
                          docentes=docentes,
                          page=page,
                          total_pages=total_pages,
                          total=total,
                          usuario=usuario)

# ============================================================================
# RUTA: LISTADO DE USUARIOS (ADMIN LOCAL)
# ============================================================================

@admin_bp.route('/usuarios')
@admin_required
def usuarios_admin_local():
    """Listar usuarios de la institución (solo admin_local)"""
    usuario = Usuario.query.get(session['usuario_id'])
    if usuario.role != 'admin_local':
        return redirect(url_for('admin.dashboard'))

    page = request.args.get('page', 1, type=int)
    per_page = 10

    query = Usuario.query.filter_by(institucion_id=usuario.institucion_id, role='docente')
    total = query.count()
    usuarios = query.order_by(Usuario.fecha_creacion.desc()).paginate(
        page=page,
        per_page=per_page,
        error_out=False
    ).items
    total_pages = math.ceil(total / per_page)

    return render_template(
        'admin_local/usuarios.html',
        usuarios=usuarios,
        page=page,
        total_pages=total_pages,
        total=total,
        usuario=usuario
    )

# ============================================================================
# RUTA: SOLICITUDES DE ESTUDIANTES (ADMIN LOCAL)
# ============================================================================

@admin_bp.route('/solicitudes-estudiantes')
@admin_required
def solicitudes_estudiantes_admin_local():
    """Listar solicitudes de estudiantes por materia (admin_local)"""
    usuario = Usuario.query.get(session['usuario_id'])
    if usuario.role != 'admin_local':
        return redirect(url_for('admin.dashboard'))

    page = request.args.get('page', 1, type=int)
    per_page = 10
    estado = request.args.get('estado', 'pendiente')

    query = SolicitudEstudianteMateria.query.join(Curso).filter(
        Curso.institucion_id == usuario.institucion_id
    )

    if estado in ['pendiente', 'aprobado', 'rechazado']:
        query = query.filter(SolicitudEstudianteMateria.estado == estado)

    total = query.count()
    solicitudes = query.order_by(SolicitudEstudianteMateria.fecha_solicitud.desc()).paginate(
        page=page,
        per_page=per_page,
        error_out=False
    ).items
    total_pages = math.ceil(total / per_page)

    return render_template(
        'admin_local/solicitudes_estudiantes.html',
        solicitudes=solicitudes,
        page=page,
        total_pages=total_pages,
        total=total,
        estado=estado,
        usuario=usuario
    )

# ============================================================================
# RUTA: APROBAR SOLICITUD (ADMIN LOCAL)
# ============================================================================

@admin_bp.route('/solicitudes-estudiantes/<int:solicitud_id>/aprobar', methods=['POST'])
@admin_required
def aprobar_solicitud_estudiante(solicitud_id):
    """Aprobar solicitud de estudiante (admin_local)"""
    try:
        usuario = Usuario.query.get(session['usuario_id'])
        if usuario.role != 'admin_local':
            return jsonify({'success': False, 'error': 'No tienes permiso'}), 403

        solicitud = SolicitudEstudianteMateria.query.get(solicitud_id)
        if not solicitud or solicitud.estado != 'pendiente':
            return jsonify({'success': False, 'error': 'Solicitud inválida'}), 404

        if solicitud.curso.institucion_id != usuario.institucion_id:
            return jsonify({'success': False, 'error': 'No tienes permiso'}), 403

        existe = EstudianteCurso.query.filter_by(
            estudiante_id=solicitud.estudiante_id,
            curso_id=solicitud.curso_id
        ).first()
        if not existe:
            db.session.add(EstudianteCurso(
                estudiante_id=solicitud.estudiante_id,
                curso_id=solicitud.curso_id
            ))

        solicitud.estado = 'aprobado'
        solicitud.admin_local_id = usuario.id
        solicitud.fecha_resolucion = datetime.utcnow()
        db.session.commit()

        return jsonify({'success': True, 'mensaje': 'Solicitud aprobada'}), 200

    except Exception as e:
        db.session.rollback()
        print(f"[ERROR] Error al aprobar solicitud: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================================
# RUTA: RECHAZAR SOLICITUD (ADMIN LOCAL)
# ============================================================================

@admin_bp.route('/solicitudes-estudiantes/<int:solicitud_id>/rechazar', methods=['POST'])
@admin_required
def rechazar_solicitud_estudiante(solicitud_id):
    """Rechazar solicitud de estudiante (admin_local)"""
    try:
        usuario = Usuario.query.get(session['usuario_id'])
        if usuario.role != 'admin_local':
            return jsonify({'success': False, 'error': 'No tienes permiso'}), 403

        data = request.get_json() or {}
        razon = data.get('razon', '').strip()

        solicitud = SolicitudEstudianteMateria.query.get(solicitud_id)
        if not solicitud or solicitud.estado != 'pendiente':
            return jsonify({'success': False, 'error': 'Solicitud inválida'}), 404

        if solicitud.curso.institucion_id != usuario.institucion_id:
            return jsonify({'success': False, 'error': 'No tienes permiso'}), 403

        solicitud.estado = 'rechazado'
        solicitud.respuesta = razon
        solicitud.admin_local_id = usuario.id
        solicitud.fecha_resolucion = datetime.utcnow()
        db.session.commit()

        return jsonify({'success': True, 'mensaje': 'Solicitud rechazada'}), 200

    except Exception as e:
        db.session.rollback()
        print(f"[ERROR] Error al rechazar solicitud: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================================
# RUTA: APROBAR DOCENTE (AJAX)
# ============================================================================

@admin_bp.route('/docentes/<int:docente_id>/aprobar', methods=['POST'])
@admin_required
def aprobar_docente(docente_id):
    """Aprobar docente (cambiar estado de pendiente a activo)"""
    try:
        docente = Usuario.query.get(docente_id)
        
        if not docente or docente.role != 'docente':
            return jsonify({'success': False, 'error': 'Docente no encontrado'}), 404
        
        if docente.estado != 'pendiente':
            return jsonify({'success': False, 'error': 'El docente no está pendiente'}), 400
        
        # Verificar permisos (solo admin_local de la misma institución)
        usuario = Usuario.query.get(session['usuario_id'])
        if usuario.role != 'admin_local' or usuario.institucion_id != docente.institucion_id:
            return jsonify({'success': False, 'error': 'No tienes permiso'}), 403
        
        docente.estado = 'activo'
        db.session.commit()
        
        print(f"[OK] Docente {docente.email} aprobado por {usuario.email}")
        
        return jsonify({
            'success': True,
            'mensaje': f'Docente {docente.nombre} aprobado exitosamente'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"[ERROR] Error al aprobar docente: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================================
# RUTA: RECHAZAR DOCENTE (AJAX)
# ============================================================================

@admin_bp.route('/docentes/<int:docente_id>/rechazar', methods=['POST'])
@admin_required
def rechazar_docente(docente_id):
    """Rechazar docente (cambiar estado a inactivo con razón)"""
    try:
        data = request.get_json()
        razon = data.get('razon', 'Sin especificar')
        
        docente = Usuario.query.get(docente_id)
        
        if not docente or docente.role != 'docente':
            return jsonify({'success': False, 'error': 'Docente no encontrado'}), 404
        
        if docente.estado != 'pendiente':
            return jsonify({'success': False, 'error': 'El docente no está pendiente'}), 400
        
        # Verificar permisos (solo admin_local de la misma institución)
        usuario = Usuario.query.get(session['usuario_id'])
        if usuario.role != 'admin_local' or usuario.institucion_id != docente.institucion_id:
            return jsonify({'success': False, 'error': 'No tienes permiso'}), 403
        
        docente.estado = 'inactivo'
        db.session.commit()
        
        print(f"[OK] Docente {docente.email} rechazado. Razón: {razon}")
        
        return jsonify({
            'success': True,
            'mensaje': f'Docente {docente.nombre} rechazado'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"[ERROR] Error al rechazar docente: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================================
# RUTA: LISTADO DE ADMINS LOCALES PENDIENTES
# ============================================================================

@admin_bp.route('/admins-locales/pendientes')
@admin_required
def admins_locales_pendientes():
    """Listar admins locales pendientes de aprobación"""
    page = request.args.get('page', 1, type=int)
    per_page = 10

    usuario = Usuario.query.get(session['usuario_id'])
    if usuario.role != 'admin_global':
        return redirect(url_for('admin.dashboard'))

    query = Usuario.query.filter_by(role='admin_local', estado='pendiente')
    total = query.count()
    admins = query.paginate(page=page, per_page=per_page, error_out=False).items
    total_pages = math.ceil(total / per_page)

    return render_template(
        'admin/admins_locales_pendientes.html',
        admins=admins,
        page=page,
        total_pages=total_pages,
        total=total
    )

# ============================================================================
# RUTA: LISTADO DE ADMINS LOCALES (TODOS)
# ============================================================================

@admin_bp.route('/admins-locales')
@admin_required
def admins_locales():
    """Listar admins locales por estado"""
    page = request.args.get('page', 1, type=int)
    per_page = 10
    estado = request.args.get('estado', 'todos')

    usuario = Usuario.query.get(session['usuario_id'])
    if usuario.role != 'admin_global':
        return redirect(url_for('admin.dashboard'))

    query = Usuario.query.filter_by(role='admin_local')
    if estado in ['pendiente', 'activo', 'inactivo', 'suspendido']:
        query = query.filter_by(estado=estado)

    total = query.count()
    admins = query.paginate(page=page, per_page=per_page, error_out=False).items
    total_pages = math.ceil(total / per_page)

    return render_template(
        'admin/admins_locales.html',
        admins=admins,
        page=page,
        total_pages=total_pages,
        total=total,
        estado=estado
    )

# ============================================================================
# RUTA: APROBAR ADMIN LOCAL (AJAX)
# ============================================================================

@admin_bp.route('/admins-locales/<int:admin_id>/aprobar', methods=['POST'])
@admin_required
def aprobar_admin_local(admin_id):
    """Aprobar admin local (cambiar estado de pendiente a activo)"""
    try:
        admin_local = Usuario.query.get(admin_id)

        if not admin_local or admin_local.role != 'admin_local':
            return jsonify({'success': False, 'error': 'Administrador no encontrado'}), 404

        if admin_local.estado != 'pendiente':
            return jsonify({'success': False, 'error': 'El admin no está pendiente'}), 400

        usuario = Usuario.query.get(session['usuario_id'])
        if usuario.role != 'admin_global':
            return jsonify({'success': False, 'error': 'No tienes permiso'}), 403

        admin_local.estado = 'activo'
        db.session.commit()

        print(f"[OK] Admin local {admin_local.email} aprobado por {usuario.email}")

        return jsonify({
            'success': True,
            'mensaje': f'Administrador {admin_local.nombre} aprobado exitosamente'
        }), 200

    except Exception as e:
        db.session.rollback()
        print(f"[ERROR] Error al aprobar admin local: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================================
# RUTA: RECHAZAR ADMIN LOCAL (AJAX)
# ============================================================================

@admin_bp.route('/admins-locales/<int:admin_id>/rechazar', methods=['POST'])
@admin_required
def rechazar_admin_local(admin_id):
    """Rechazar admin local (cambiar estado a inactivo con razón)"""
    try:
        data = request.get_json()
        razon = data.get('razon', 'Sin especificar')

        admin_local = Usuario.query.get(admin_id)

        if not admin_local or admin_local.role != 'admin_local':
            return jsonify({'success': False, 'error': 'Administrador no encontrado'}), 404

        if admin_local.estado != 'pendiente':
            return jsonify({'success': False, 'error': 'El admin no está pendiente'}), 400

        usuario = Usuario.query.get(session['usuario_id'])
        if usuario.role != 'admin_global':
            return jsonify({'success': False, 'error': 'No tienes permiso'}), 403

        admin_local.estado = 'inactivo'
        db.session.commit()

        print(f"[OK] Admin local {admin_local.email} rechazado. Razón: {razon}")

        return jsonify({
            'success': True,
            'mensaje': f'Administrador {admin_local.nombre} rechazado'
        }), 200

    except Exception as e:
        db.session.rollback()
        print(f"[ERROR] Error al rechazar admin local: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================================
# RUTA: CAMBIAR CONTRASEÑA (AJAX)
# ============================================================================

@admin_bp.route('/perfil/cambiar-password', methods=['POST'])
@admin_required
def cambiar_password():
    """Cambiar contraseña del usuario autenticado"""
    try:
        data = request.get_json()
        current_password = data.get('current_password', '')
        new_password = data.get('new_password', '')

        usuario = Usuario.query.get(session['usuario_id'])
        if not usuario:
            return jsonify({'success': False, 'error': 'Usuario no encontrado'}), 404

        if not verificar_contraseña(current_password, usuario.password):
            return jsonify({'success': False, 'error': 'Contraseña actual incorrecta'}), 400

        es_valida, mensaje = validar_contraseña(new_password)
        if not es_valida:
            return jsonify({'success': False, 'error': mensaje}), 400

        usuario.password = encriptar_contraseña(new_password)
        db.session.commit()

        return jsonify({'success': True, 'mensaje': 'Contraseña actualizada'}), 200

    except Exception as e:
        db.session.rollback()
        print(f"[ERROR] Error al cambiar contraseña: {e}")
        return jsonify({'success': False, 'error': 'Error al actualizar contraseña'}), 500

# ============================================================================
# RUTA: LISTADO DE CURSOS
# ============================================================================

@admin_bp.route('/cursos')
@admin_required
def cursos():
    """Listar cursos con paginación"""
    page = request.args.get('page', 1, type=int)
    per_page = 10
    estado = (request.args.get('estado') or 'todas').strip().lower()
    
    usuario = Usuario.query.get(session['usuario_id'])
    
    # Si es admin_local, solo ver su institución
    if usuario.role == 'admin_local':
        query = Curso.query.filter_by(institucion_id=usuario.institucion_id)
    else:
        query = Curso.query

    if estado == 'activas':
        query = query.filter(Curso.activo.is_(True))
    elif estado == 'inactivas':
        query = query.filter(Curso.activo.is_(False))

    query = query.order_by(Curso.activo.desc(), Curso.nombre.asc())
    
    total = query.count()
    cursos_list = query.paginate(page=page, per_page=per_page, error_out=False).items
    
    total_pages = math.ceil(total / per_page)
    
    # Obtener períodos activos para el form
    periodos = Periodo.query.filter_by(activo=True).all()
    
    # Obtener docentes disponibles
    docentes_query = Usuario.query.filter_by(role='docente', estado='activo')
    if usuario.role == 'admin_local':
        docentes_query = docentes_query.filter_by(institucion_id=usuario.institucion_id)
    docentes = docentes_query.all()

    instituciones = []
    if usuario.role == 'admin_global':
        instituciones = Institucion.query.filter_by(activo=True).order_by(Institucion.nombre.asc()).all()
    
    template_name = 'admin/cursos.html'
    if usuario.role == 'admin_local':
        template_name = 'admin_local/cursos.html'

    return render_template(template_name,
                          cursos=cursos_list,
                          page=page,
                          total_pages=total_pages,
                          total=total,
                          estado=estado,
                          periodos=periodos,
                          docentes=docentes,
                          instituciones=instituciones,
                          usuario=usuario)

# ============================================================================
# RUTA: DETALLE DE CURSO (ADMIN LOCAL)
# ============================================================================

@admin_bp.route('/cursos/<int:curso_id>/detalle')
@admin_required
def detalle_curso_admin_local(curso_id):
    """Vista de detalle del curso para admin local"""
    usuario = Usuario.query.get(session['usuario_id'])
    if usuario.role != 'admin_local':
        return redirect(url_for('admin.dashboard'))

    curso = Curso.query.get(curso_id)
    if not curso or curso.institucion_id != usuario.institucion_id:
        return redirect(url_for('admin.cursos'))

    docentes_disponibles = Usuario.query.filter_by(
        role='docente',
        estado='activo',
        institucion_id=usuario.institucion_id
    ).all()

    estudiantes_rel = EstudianteCurso.query.filter_by(curso_id=curso_id).all()
    estudiantes = [rel.estudiante for rel in estudiantes_rel]

    return render_template(
        'admin_local/curso_detalle.html',
        curso=curso,
        docentes=docentes_disponibles,
        estudiantes=estudiantes,
        total_estudiantes=len(estudiantes)
    )

# ============================================================================
# RUTA: CREAR CURSO (AJAX)
# ============================================================================

@admin_bp.route('/cursos/crear', methods=['POST'])
@admin_required
def crear_curso():
    """Crear nuevo curso"""
    try:
        data = request.get_json()
        
        usuario = Usuario.query.get(session['usuario_id'])
        
        # Validar campos
        nombre = data.get('nombre', '').strip()
        codigo = data.get('codigo', '').strip()
        periodo_nombre = data.get('periodo_nombre', '').strip()
        fecha_inicio = data.get('fecha_inicio', '').strip()
        fecha_fin = data.get('fecha_fin', '').strip()
        docente_principal_id = data.get('docente_principal_id')
        institucion_id = data.get('institucion_id')
        creditos = data.get('creditos', 3)
        descripcion = data.get('descripcion', '').strip()
        dias_semana = data.get('dias_semana', '').strip()
        sesiones_por_semana = data.get('sesiones_por_semana', 0)
        
        if not all([nombre, codigo, periodo_nombre, fecha_inicio, fecha_fin]):
            return jsonify({'success': False, 'error': 'Campos requeridos vacíos'}), 400

        try:
            inicio = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
            fin = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'success': False, 'error': 'Fechas inválidas'}), 400

        if fin < inicio:
            return jsonify({'success': False, 'error': 'La fecha fin debe ser mayor a la fecha inicio'}), 400

        if usuario.role == 'admin_global':
            if not institucion_id:
                return jsonify({'success': False, 'error': 'Debes seleccionar una institución'}), 400
            try:
                institucion_id = int(institucion_id)
            except (TypeError, ValueError):
                return jsonify({'success': False, 'error': 'Institución inválida'}), 400

            institucion = Institucion.query.get(institucion_id)
            if not institucion or not institucion.activo:
                return jsonify({'success': False, 'error': 'Institución no disponible'}), 404
        else:
            institucion_id = usuario.institucion_id

        periodo = Periodo.query.filter_by(
            institucion_id=institucion_id,
            nombre=periodo_nombre
        ).first()

        if not periodo:
            periodo = Periodo(
                institucion_id=institucion_id,
                nombre=periodo_nombre,
                fecha_inicio=inicio,
                fecha_fin=fin,
                activo=True
            )
            db.session.add(periodo)
        else:
            periodo.fecha_inicio = inicio
            periodo.fecha_fin = fin
            periodo.activo = True
        
        db.session.flush()
        
        docente_principal = None
        if docente_principal_id:
            try:
                docente_principal_id = int(docente_principal_id)
            except (TypeError, ValueError):
                return jsonify({'success': False, 'error': 'Docente inválido'}), 400

            docente_principal = Usuario.query.get(docente_principal_id)
            if not docente_principal or docente_principal.role != 'docente':
                return jsonify({'success': False, 'error': 'Docente no encontrado'}), 404

            if docente_principal.estado != 'activo':
                return jsonify({'success': False, 'error': 'Docente no disponible'}), 400

            if usuario.role == 'admin_local' and docente_principal.institucion_id != usuario.institucion_id:
                return jsonify({'success': False, 'error': 'Docente no disponible'}), 400

        # Crear curso
        nuevo_curso = Curso(
            institucion_id=institucion_id,
            periodo_id=periodo.id,
            nombre=nombre,
            codigo=codigo,
            creditos=creditos,
            descripcion=descripcion,
            dias_semana=dias_semana or None,
            sesiones_por_semana=sessions_per_week if (sessions_per_week := (int(sesiones_por_semana) if isinstance(sesiones_por_semana, int) or (isinstance(sesiones_por_semana, str) and sesiones_por_semana.isdigit()) else 0)) is not None else 0,
            docente_principal_id=docente_principal.id if docente_principal else None,
            activo=True
        )
        
        db.session.add(nuevo_curso)
        db.session.commit()
        
        print(f"[OK] Curso creado: {codigo} - {nombre}")
        
        return jsonify({
            'success': True,
            'mensaje': 'Curso creado exitosamente',
            'curso_id': nuevo_curso.id
        }), 201
        
    except Exception as e:
        db.session.rollback()
        print(f"[ERROR] Error al crear curso: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================================
# RUTA: ASIGNAR DOCENTE PRINCIPAL A CURSO (ADMIN LOCAL)
# ============================================================================

@admin_bp.route('/cursos/<int:curso_id>/asignar-docente', methods=['POST'])
@admin_required
def asignar_docente_principal(curso_id):
    """Asignar docente principal a un curso (admin_local)"""
    try:
        usuario = Usuario.query.get(session['usuario_id'])
        if usuario.role != 'admin_local':
            return jsonify({'success': False, 'error': 'No tienes permiso'}), 403

        data = request.get_json() or {}
        docente_id = data.get('docente_id')
        if not docente_id:
            return jsonify({'success': False, 'error': 'Docente requerido'}), 400

        curso = Curso.query.get(curso_id)
        if not curso or curso.institucion_id != usuario.institucion_id:
            return jsonify({'success': False, 'error': 'Materia no encontrada'}), 404

        docente = Usuario.query.get(docente_id)
        if not docente or docente.role != 'docente':
            return jsonify({'success': False, 'error': 'Docente no encontrado'}), 404

        if docente.estado != 'activo' or docente.institucion_id != usuario.institucion_id:
            return jsonify({'success': False, 'error': 'Docente no disponible'}), 400

        if curso.docente_principal_id == docente.id:
            return jsonify({'success': True, 'mensaje': 'Docente ya asignado'}), 200

        curso.docente_principal_id = docente.id
        db.session.commit()

        return jsonify({
            'success': True,
            'mensaje': 'Docente asignado correctamente'
        }), 200

    except Exception as e:
        db.session.rollback()
        print(f"[ERROR] Error al asignar docente: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================================
# RUTA: CARGAR LISTA DE ESTUDIANTES (ADMIN LOCAL)
# ============================================================================

@admin_bp.route('/cursos/<int:curso_id>/cargar-estudiantes', methods=['POST'])
@admin_required
def cargar_estudiantes(curso_id):
    """Cargar estudiantes desde CSV en una materia (admin_local) - OPTIMIZADO CON BULK"""
    print(f"[DEBUG] Iniciando carga de estudiantes para curso_id: {curso_id}")
    
    try:
        # Validar sesión y permisos (rápido)
        if 'usuario_id' not in session:
            return jsonify({'success': False, 'error': 'Sesión expirada'}), 401
        
        usuario = Usuario.query.get(session['usuario_id'])
        if not usuario or usuario.role != 'admin_local':
            return jsonify({'success': False, 'error': 'No tienes permiso'}), 403

        curso = Curso.query.get(curso_id)
        if not curso or curso.institucion_id != usuario.institucion_id:
            return jsonify({'success': False, 'error': 'Materia no encontrada'}), 404

        # Validar archivo
        archivo = request.files.get('archivo')
        if not archivo or not archivo.filename or not archivo.filename.lower().endswith('.csv'):
            return jsonify({'success': False, 'error': 'Archivo CSV requerido'}), 400

        print(f"[DEBUG] Procesando archivo: {archivo.filename}")
        
        # Leer y validar CSV completo
        content = io.TextIOWrapper(archivo.stream, encoding='utf-8-sig')
        reader = csv.DictReader(content)
        
        if not reader.fieldnames:
            return jsonify({'success': False, 'error': 'CSV vacío'}), 400
        
        fieldnames_lower = [n.strip().lower() for n in reader.fieldnames]
        requeridos = {'email', 'nombre', 'apellido'}
        if not requeridos.issubset(set(fieldnames_lower)):
            return jsonify({
                'success': False, 
                'error': f'Columnas requeridas: email, nombre, apellido'
            }), 400

        # ===== PASO 1: Leer y validar todos los datos del CSV =====
        registros_validos = []
        vistos = set()
        errores = 0

        for num_fila, row in enumerate(reader, start=2):
            email = (row.get('email') or '').strip().lower()
            nombre = (row.get('nombre') or '').strip()
            apellido = (row.get('apellido') or '').strip()

            if not email or not nombre or not apellido:
                errores += 1
                continue

            if email in vistos:
                continue
            vistos.add(email)

            es_valido, _ = validar_email(email)
            if not es_valido:
                errores += 1
                continue

            registros_validos.append({
                'email': email,
                'nombre': nombre,
                'apellido': apellido
            })

        print(f"[DEBUG] Registros válidos: {len(registros_validos)}, Errores: {errores}")
        
        if not registros_validos:
            return jsonify({
                'success': False,
                'error': 'No hay registros válidos en el CSV'
            }), 400

        # ===== PASO 2: Obtener todos los emails existentes de UNA SOLA VEZ =====
        emails_csv = [r['email'] for r in registros_validos]
        usuarios_existentes = db.session.query(Usuario.email).filter(
            Usuario.email.in_(emails_csv),
            Usuario.institucion_id == usuario.institucion_id
        ).all()
        emails_existentes = {u.email for u in usuarios_existentes}
        print(f"[DEBUG] Usuarios existentes en BD: {len(emails_existentes)}")

        # ===== PASO 3: Separar a crear vs ya existen =====
        registros_crear = [r for r in registros_validos if r['email'] not in emails_existentes]
        print(f"[DEBUG] Nuevos estudiantes a crear: {len(registros_crear)}")

        # ===== PASO 4: Crear nuevos usuarios en BULK =====
        nuevos_usuarios = []
        if registros_crear:
            for reg in registros_crear:
                nuevo_usuario = Usuario(
                    institucion_id=usuario.institucion_id,
                    email=reg['email'],
                    password=encriptar_contraseña('Estudiante123!'),
                    nombre=reg['nombre'],
                    apellido=reg['apellido'],
                    role='estudiante',
                    estado='activo'
                )
                nuevos_usuarios.append(nuevo_usuario)
            
            db.session.bulk_save_objects(nuevos_usuarios)
            db.session.flush()  # Flush para obtener IDs sin commit
            """Cargar estudiantes desde CSV - ULTRA OPTIMIZADO SQL DIRECTO"""

        # ===== PASO 5: Obtener IDs de TODOS los estudiantes (nuevos + existentes) =====
        todos_emails = [r['email'] for r in registros_validos]
                # Validaciones rápidas
            Usuario.email.in_(todos_emails),
            Usuario.institucion_id == usuario.institucion_id
        ).all()
        
        email_a_id = {e.email: e.id for e in estudiantes_bd}
        print(f"[DEBUG] Total de estudiantes en BD: {len(email_a_id)}")

        # ===== PASO 6: Obtener inscripciones EXISTENTES de UNA SOLA VEZ =====
        student_ids = list(email_a_id.values())
        inscripciones_existentes = db.session.query(EstudianteCurso.estudiante_id).filter(
            EstudianteCurso.estudiante_id.in_(student_ids),
            EstudianteCurso.curso_id == curso_id
        ).all()
        ids_inscritos = {e.estudiante_id for e in inscripciones_existentes}
        print(f"[DEBUG] Ya inscritos en este curso: {len(ids_inscritos)}")

        for email in todos_emails:
            student_id = email_a_id[email]
            if student_id not in ids_inscritos:
                nuevas_inscripciones.append(
                    EstudianteCurso(
                        estudiante_id=student_id,
                        curso_id=curso_id
                    )
                )
        
                    return jsonify({'success': False, 'error': 'Columnas: email, nombre, apellido'}), 400
        # ===== PASO 8: Commit final =====

        creados = len(registros_crear)
        inscritos = len(nuevas_inscripciones)
        omitidos = len(registros_validos) - inscritos - len([r for r in registros_validos if r['email'] in ids_inscritos])

        print(f"[SUCCESS] Carga completada. Creados: {creados}, Inscritos: {inscritos}")
        
        mensaje = f'✅ Carga exitosa!\n✓ Creados: {creados}\n✓ Inscritos: {inscritos}'
        if errores > 0:
                    if not email or not nombre or not apellido or email in vistos:

        return jsonify({
            'inscritos': inscritos,
        }), 200

    except Exception as e:
        db.session.rollback()
        print(f"[ERROR] Error al cargar estudiantes: {type(e).__name__}: {str(e)}")
                    registros.append({
        traceback.print_exc()
        return jsonify({
            'success': False, 
            'error': f'Error: {str(e)}'
        }), 500
                if not registros:
# ============================================================================

@admin_bp.route('/cursos/<int:curso_id>/actualizar', methods=['POST'])
@admin_required
def actualizar_curso(curso_id):
                print(f"[DEBUG] Total registros válidos: {len(registros)}")

                # SQL DIRECTO: MUCHO MÁS RÁPIDO
                from sqlalchemy import text
                from datetime import datetime

                emails_csv = [r['email'] for r in registros]
            
                # Paso 1: Obtener emails que YA existen
                result = db.session.execute(text("""
                    SELECT email FROM usuarios 
                    WHERE email = ANY(:emails) 
                    AND institucion_id = :inst_id
                """), {'emails': emails_csv, 'inst_id': usuario.institucion_id})
            
                emails_existentes = {row[0] for row in result}
                registros_nuevos = [r for r in registros if r['email'] not in emails_existentes]
            
                print(f"[DEBUG] Nuevos a crear: {len(registros_nuevos)}, Ya existían: {len(emails_existentes)}")

                creados = 0
                if registros_nuevos:
                    # Paso 2: INSERT usuarios nuevos con SQL
                    pwd_encriptada = encriptar_contraseña('Estudiante123!')
                    now = datetime.utcnow()
                
                    for reg in registros_nuevos:
                        db.session.execute(text("""
                            INSERT INTO usuarios 
                            (institucion_id, email, password, nombre, apellido, role, estado, fecha_creacion, fecha_actualizacion)
                            VALUES (:inst_id, :email, :pwd, :nombre, :apellido, 'estudiante', 'activo', :now, :now)
                        """), {
                            'inst_id': usuario.institucion_id,
                            'email': reg['email'],
                            'pwd': pwd_encriptada,
                            'nombre': reg['nombre'],
                            'apellido': reg['apellido'],
                            'now': now
                        })
                
                    db.session.commit()
                    creados = len(registros_nuevos)
                    print(f"[DEBUG] {creados} usuarios creados")

                # Paso 3: Obtener IDs de estudiantes (nuevos + existentes)
                result = db.session.execute(text("""
                    SELECT id FROM usuarios 
                    WHERE email = ANY(:emails) 
                    AND institucion_id = :inst_id
                """), {'emails': emails_csv, 'inst_id': usuario.institucion_id})
            
                estudiante_ids = [row[0] for row in result]
                print(f"[DEBUG] IDs de estudiantes obtenidos: {len(estudiante_ids)}")

                # Paso 4: Obtener inscritos ya en este curso
                result = db.session.execute(text("""
                    SELECT estudiante_id FROM estudiante_curso
                    WHERE curso_id = :curso_id
                """), {'curso_id': curso_id})
            
                ids_ya_inscritos = {row[0] for row in result}
                print(f"[DEBUG] Ya inscritos en curso: {len(ids_ya_inscritos)}")

                # Paso 5: INSERT inscripciones nuevas con SQL
                inscritos = 0
                for sid in estudiante_ids:
                    if sid not in ids_ya_inscritos:
                        db.session.execute(text("""
                            INSERT INTO estudiante_curso (estudiante_id, curso_id)
                            VALUES (:sid, :cid)
                        """), {'sid': sid, 'cid': curso_id})
                        inscritos += 1
                return jsonify({'success': False, 'error': 'La fecha fin debe ser mayor a la fecha inicio'}), 400
                if inscritos > 0:
                    db.session.commit()
                    print(f"[DEBUG] {inscritos} nuevas inscripciones")

                mensaje = f'✅ Éxito!\n✓ Creados: {creados}\n✓ Inscritos: {inscritos}'
            periodo = Periodo.query.filter_by(
                institucion_id=institucion_id,
                nombre=periodo_nombre
            ).first()

            if not periodo:
                periodo = Periodo(
                    institucion_id=curso.institucion_id,
                    nombre=periodo_nombre,
                    fecha_inicio=inicio,
                    fecha_fin=fin,
                    activo=True
                )
                print(f"[ERROR] {type(e).__name__}: {str(e)}")
            else:
                periodo.fecha_inicio = inicio
                periodo.fecha_fin = fin
                periodo.activo = True

            db.session.flush()

            curso.periodo_id = periodo.id
        
        db.session.commit()
        
        print(f"[OK] Curso actualizado: {curso.codigo}")
        
        return jsonify({
            'success': True,
            'mensaje': 'Curso actualizado exitosamente'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"[ERROR] Error al actualizar curso: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================================
# RUTA: ELIMINAR CURSO (AJAX)
# ============================================================================

@admin_bp.route('/cursos/<int:curso_id>/eliminar', methods=['POST'])
@admin_required
def eliminar_curso(curso_id):
    """Eliminar curso (soft delete - marcar como inactivo)"""
    try:
        curso = Curso.query.get(curso_id)
        if not curso:
            return jsonify({'success': False, 'error': 'Curso no encontrado'}), 404
        
        usuario = Usuario.query.get(session['usuario_id'])
        if usuario.role == 'admin_local' and usuario.institucion_id != curso.institucion_id:
            return jsonify({'success': False, 'error': 'No tienes permiso'}), 403
        
        # Soft delete
        curso.activo = False
        db.session.commit()
        
        print(f"[OK] Curso eliminado (inactivado): {curso.codigo}")
        
        return jsonify({
            'success': True,
            'mensaje': 'Curso eliminado exitosamente'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"[ERROR] Error al eliminar curso: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================================
# RUTA: LISTADO DE INSTITUCIONES
# ============================================================================

@admin_bp.route('/instituciones')
@admin_required
def instituciones():
    """Listar instituciones (solo para admin_global)"""
    usuario = Usuario.query.get(session['usuario_id'])
    
    if usuario.role != 'admin_global':
        return redirect(url_for('admin.dashboard'))
    
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    total = Institucion.query.count()
    instituciones_list = Institucion.query.paginate(page=page, per_page=per_page, error_out=False).items
    
    total_pages = math.ceil(total / per_page)
    
    return render_template('admin/instituciones.html',
                          instituciones=instituciones_list,
                          page=page,
                          total_pages=total_pages,
                          total=total)

# ============================================================================
# RUTA: CREAR INSTITUCIÓN (AJAX)
# ============================================================================

@admin_bp.route('/instituciones/crear', methods=['POST'])
@admin_required
def crear_institucion():
    """Crear nueva institución (solo admin_global)"""
    try:
        usuario = Usuario.query.get(session['usuario_id'])
        if usuario.role != 'admin_global':
            return jsonify({'success': False, 'error': 'No tienes permiso'}), 403
        
        data = request.get_json()
        
        nombre = data.get('nombre', '').strip()
        ciudad = data.get('ciudad', '').strip()
        pais = data.get('pais', '').strip()
        
        if not all([nombre, ciudad, pais]):
            return jsonify({'success': False, 'error': 'Campos requeridos vacíos'}), 400
        
        # Verificar que no exista ya
        if Institucion.query.filter_by(nombre=nombre).first():
            return jsonify({'success': False, 'error': 'Esta institución ya existe'}), 409
        
        nueva_inst = Institucion(
            nombre=nombre,
            ciudad=ciudad,
            pais=pais,
            activo=True
        )
        
        db.session.add(nueva_inst)
        db.session.commit()
        
        print(f"[OK] Institución creada: {nombre}")
        
        return jsonify({
            'success': True,
            'mensaje': 'Institución creada exitosamente',
            'institucion_id': nueva_inst.id
        }), 201
        
    except Exception as e:
        db.session.rollback()
        print(f"[ERROR] Error al crear institución: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================================
# RUTA: ACTUALIZAR INSTITUCIÓN (AJAX)
# ============================================================================

@admin_bp.route('/instituciones/<int:inst_id>/actualizar', methods=['POST'])
@admin_required
def actualizar_institucion(inst_id):
    """Actualizar institución (solo admin_global)"""
    try:
        usuario = Usuario.query.get(session['usuario_id'])
        if usuario.role != 'admin_global':
            return jsonify({'success': False, 'error': 'No tienes permiso'}), 403
        
        institucion = Institucion.query.get(inst_id)
        if not institucion:
            return jsonify({'success': False, 'error': 'Institución no encontrada'}), 404
        
        data = request.get_json()
        
        institucion.nombre = data.get('nombre', institucion.nombre).strip()
        institucion.ciudad = data.get('ciudad', institucion.ciudad).strip()
        institucion.pais = data.get('pais', institucion.pais).strip()
        
        db.session.commit()
        
        print(f"[OK] Institución actualizada: {institucion.nombre}")
        
        return jsonify({
            'success': True,
            'mensaje': 'Institución actualizada exitosamente'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"[ERROR] Error al actualizar institución: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================================
# RUTA: ELIMINAR INSTITUCIÓN (AJAX)
# ============================================================================

@admin_bp.route('/instituciones/<int:inst_id>/eliminar', methods=['POST'])
@admin_required
def eliminar_institucion(inst_id):
    """Eliminar institución (soft delete)"""
    try:
        usuario = Usuario.query.get(session['usuario_id'])
        if usuario.role != 'admin_global':
            return jsonify({'success': False, 'error': 'No tienes permiso'}), 403
        
        institucion = Institucion.query.get(inst_id)
        if not institucion:
            return jsonify({'success': False, 'error': 'Institución no encontrada'}), 404
        
        institucion.activo = False
        db.session.commit()
        
        print(f"[OK] Institución eliminada (inactivada): {institucion.nombre}")
        
        return jsonify({
            'success': True,
            'mensaje': 'Institución eliminada exitosamente'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"[ERROR] Error al eliminar institución: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
