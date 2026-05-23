"""Rutas administrativas - Admin Global"""
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session
from extensions import db
from models import Usuario, Institucion, Curso, Periodo, CursoDocente, EstudianteCurso, SolicitudEstudianteMateria, SolicitudNuevoEstudiante
from utils import validar_email, validar_contraseña, encriptar_contraseña, verificar_contraseña, crear_usuario_con_contraseña_temporal, generar_contraseña_temporal
from functools import wraps
from datetime import datetime
import csv
import io
import math
import os
from werkzeug.utils import secure_filename

LOGOS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'imagenes', 'instituciones')
ALLOWED_LOGO_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'}

def _allowed_logo(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_LOGO_EXTENSIONS

def _save_logo(file, inst_id):
    """Guarda el archivo de logo y devuelve el filename guardado, o None."""
    if not file or file.filename == '':
        return None
    if not _allowed_logo(file.filename):
        return None
    ext = file.filename.rsplit('.', 1)[1].lower()
    filename = secure_filename(f'inst_{inst_id}.{ext}')
    os.makedirs(LOGOS_DIR, exist_ok=True)
    file.save(os.path.join(LOGOS_DIR, filename))
    return filename

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
    """Cargar estudiantes desde CSV en una materia (admin_local)."""
    try:
        if 'usuario_id' not in session:
            return jsonify({'success': False, 'error': 'Sesión expirada'}), 401

        usuario = Usuario.query.get(session['usuario_id'])
        if not usuario or usuario.role != 'admin_local':
            return jsonify({'success': False, 'error': 'No tienes permiso'}), 403

        curso = Curso.query.get(curso_id)
        if not curso or curso.institucion_id != usuario.institucion_id:
            return jsonify({'success': False, 'error': 'Materia no encontrada'}), 404

        archivo = request.files.get('archivo')
        if not archivo or not archivo.filename or not archivo.filename.lower().endswith('.csv'):
            return jsonify({'success': False, 'error': 'Archivo CSV requerido'}), 400

        content = io.TextIOWrapper(archivo.stream, encoding='utf-8-sig')
        reader = csv.DictReader(content)

        if not reader.fieldnames:
            return jsonify({'success': False, 'error': 'CSV vacío'}), 400

        fieldnames_lower = [nombre.strip().lower() for nombre in reader.fieldnames]
        requeridos = {'email', 'nombre', 'apellido'}
        if not requeridos.issubset(set(fieldnames_lower)):
            return jsonify({'success': False, 'error': 'Columnas requeridas: email, nombre, apellido'}), 400

        registros_validos = []
        vistos = set()
        errores = 0

        for row in reader:
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

            registros_validos.append({'email': email, 'nombre': nombre, 'apellido': apellido})

        if not registros_validos:
            return jsonify({'success': False, 'error': 'No hay registros válidos en el CSV'}), 400

        emails_csv = [registro['email'] for registro in registros_validos]
        usuarios_existentes = Usuario.query.filter(
            Usuario.email.in_(emails_csv),
            Usuario.institucion_id == usuario.institucion_id
        ).all()
        emails_existentes = {usuario_existente.email for usuario_existente in usuarios_existentes}

        registros_crear = [registro for registro in registros_validos if registro['email'] not in emails_existentes]
        creados = 0
        if registros_crear:
            nuevos_usuarios = []
            for registro in registros_crear:
                nuevos_usuarios.append(
                    Usuario(
                        institucion_id=usuario.institucion_id,
                        email=registro['email'],
                        password=encriptar_contraseña('Estudiante123!'),
                        nombre=registro['nombre'],
                        apellido=registro['apellido'],
                        role='estudiante',
                        estado='activo'
                    )
                )
            db.session.bulk_save_objects(nuevos_usuarios)
            db.session.flush()
            creados = len(nuevos_usuarios)

        estudiantes = Usuario.query.with_entities(Usuario.id, Usuario.email).filter(
            Usuario.email.in_(emails_csv),
            Usuario.institucion_id == usuario.institucion_id
        ).all()
        email_a_id = {email: estudiante_id for estudiante_id, email in estudiantes}

        inscripciones_existentes = EstudianteCurso.query.with_entities(EstudianteCurso.estudiante_id).filter(
            EstudianteCurso.curso_id == curso.id,
            EstudianteCurso.estudiante_id.in_(list(email_a_id.values()))
        ).all()
        ids_inscritos = {estudiante_id for (estudiante_id,) in inscripciones_existentes}

        nuevas_inscripciones = []
        for email in emails_csv:
            estudiante_id = email_a_id.get(email)
            if estudiante_id and estudiante_id not in ids_inscritos:
                nuevas_inscripciones.append(EstudianteCurso(estudiante_id=estudiante_id, curso_id=curso.id))

        if nuevas_inscripciones:
            db.session.bulk_save_objects(nuevas_inscripciones)

        db.session.commit()

        inscritos = len(nuevas_inscripciones)
        mensaje = f'Carga finalizada. Creados: {creados}, inscritos: {inscritos}, errores: {errores}'
        return jsonify({
            'success': True,
            'mensaje': mensaje,
            'creados': creados,
            'inscritos': inscritos,
            'errores': errores
        }), 200

    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'Error: {str(e)}'}), 500

# ============================================================================
# RUTA: CARGAR ESTUDIANTES POR LOTE (PROCESA UN LOTE A LA VEZ)
# ============================================================================

@admin_bp.route('/cursos/<int:curso_id>/cargar-estudiantes-lote', methods=['POST'])
@admin_required
def cargar_estudiantes_lote(curso_id):
    """Cargar un lote de estudiantes (para evitar timeouts)."""
    try:
        if 'usuario_id' not in session:
            return jsonify({'success': False, 'error': 'Sesión expirada'}), 401

        usuario = Usuario.query.get(session['usuario_id'])
        if not usuario or usuario.role != 'admin_local':
            return jsonify({'success': False, 'error': 'No tienes permiso'}), 403

        curso = Curso.query.get(curso_id)
        if not curso or curso.institucion_id != usuario.institucion_id:
            return jsonify({'success': False, 'error': 'Materia no encontrada'}), 404

        data = request.get_json(silent=True) or {}
        registros = data.get('registros', [])

        if not registros:
            return jsonify({'success': False, 'error': 'No hay registros para procesar'}), 400

        creados = 0
        inscritos = 0

        # Procesar cada registro del lote
        emails_lote = [r['email'].lower().strip() for r in registros if r.get('email')]
        
        # Obtener usuarios existentes
        usuarios_existentes = Usuario.query.filter(
            Usuario.email.in_(emails_lote),
            Usuario.institucion_id == usuario.institucion_id
        ).all()
        emails_existentes = {u.email for u in usuarios_existentes}

        # Crear nuevos usuarios
        registros_crear = [r for r in registros if r.get('email', '').lower().strip() not in emails_existentes]
        
        if registros_crear:
            nuevos_usuarios = []
            for registro in registros_crear:
                email = registro.get('email', '').lower().strip()
                nombre = registro.get('nombre', '').strip()
                apellido = registro.get('apellido', '').strip()
                
                if not email or not nombre or not apellido:
                    continue
                
                es_valido, _ = validar_email(email)
                if not es_valido:
                    continue
                
                nuevos_usuarios.append(
                    Usuario(
                        institucion_id=usuario.institucion_id,
                        email=email,
                        password=encriptar_contraseña('Estudiante123!'),
                        nombre=nombre,
                        apellido=apellido,
                        role='estudiante',
                        estado='activo'
                    )
                )
            
            if nuevos_usuarios:
                db.session.bulk_save_objects(nuevos_usuarios)
                db.session.flush()
                creados = len(nuevos_usuarios)

        # Obtener IDs de estudiantes
        estudiantes = Usuario.query.with_entities(Usuario.id, Usuario.email).filter(
            Usuario.email.in_(emails_lote),
            Usuario.institucion_id == usuario.institucion_id
        ).all()
        email_a_id = {email: estudiante_id for estudiante_id, email in estudiantes}

        # Obtener inscripciones existentes
        inscripciones_existentes = EstudianteCurso.query.with_entities(EstudianteCurso.estudiante_id).filter(
            EstudianteCurso.curso_id == curso.id,
            EstudianteCurso.estudiante_id.in_(list(email_a_id.values()))
        ).all()
        ids_inscritos = {estudiante_id for (estudiante_id,) in inscripciones_existentes}

        # Crear nuevas inscripciones
        nuevas_inscripciones = []
        for email in emails_lote:
            estudiante_id = email_a_id.get(email)
            if estudiante_id and estudiante_id not in ids_inscritos:
                nuevas_inscripciones.append(EstudianteCurso(estudiante_id=estudiante_id, curso_id=curso.id))

        if nuevas_inscripciones:
            db.session.bulk_save_objects(nuevas_inscripciones)
            inscritos = len(nuevas_inscripciones)

        db.session.commit()

        return jsonify({
            'success': True,
            'creados': creados,
            'inscritos': inscritos
        }), 200

    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'Error en lote: {str(e)}'}), 500

# ============================================================================
# RUTA: ACTUALIZAR CURSO (AJAX)
# ============================================================================

@admin_bp.route('/cursos/<int:curso_id>/actualizar', methods=['POST'])
@admin_required
def actualizar_curso(curso_id):
    """Actualizar curso existente."""
    try:
        data = request.get_json(silent=True) or {}

        curso = Curso.query.get(curso_id)
        if not curso:
            return jsonify({'success': False, 'error': 'Curso no encontrado'}), 404

        usuario = Usuario.query.get(session['usuario_id'])
        if usuario.role == 'admin_local' and usuario.institucion_id != curso.institucion_id:
            return jsonify({'success': False, 'error': 'No tienes permiso'}), 403

        if data.get('codigo') is not None:
            curso.codigo = data.get('codigo', '').strip()
        if data.get('nombre') is not None:
            curso.nombre = data.get('nombre', '').strip()
        if data.get('descripcion') is not None:
            curso.descripcion = (data.get('descripcion') or '').strip()
        if data.get('creditos') not in (None, ''):
            curso.creditos = int(data.get('creditos'))
        if 'docente_principal_id' in data:
            docente_principal_id = data.get('docente_principal_id')
            curso.docente_principal_id = int(docente_principal_id) if docente_principal_id not in (None, '', 'null') else None
        if 'dias_semana' in data:
            curso.dias_semana = (data.get('dias_semana') or '').strip() or None
        if 'sesiones_por_semana' in data:
            sesiones = data.get('sesiones_por_semana')
            curso.sesiones_por_semana = int(sesiones) if sesiones not in (None, '', 'null') else 0

        periodo_nombre = (data.get('periodo_nombre') or '').strip()
        fecha_inicio = (data.get('fecha_inicio') or '').strip()
        fecha_fin = (data.get('fecha_fin') or '').strip()

        if periodo_nombre:
            if not fecha_inicio or not fecha_fin:
                return jsonify({'success': False, 'error': 'Debes indicar fecha inicio y fecha fin'}), 400

            inicio = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
            fin = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
            if fin <= inicio:
                return jsonify({'success': False, 'error': 'La fecha fin debe ser mayor a la fecha inicio'}), 400

            periodo = Periodo.query.filter_by(
                institucion_id=curso.institucion_id,
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
                db.session.add(periodo)
                db.session.flush()
            else:
                periodo.fecha_inicio = inicio
                periodo.fecha_fin = fin
                periodo.activo = True

            curso.periodo_id = periodo.id

        db.session.commit()

        return jsonify({
            'success': True,
            'mensaje': 'Curso actualizado exitosamente'
        }), 200

    except ValueError as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400

# ============================================================================
# RUTA: Solicitudes de Nuevos Estudiantes (ADMIN LOCAL)
# ============================================================================

@admin_bp.route('/solicitudes-nuevos-estudiantes')
@admin_required
def solicitudes_nuevos_estudiantes():
    """Ver solicitudes de nuevos estudiantes (admin_local)"""
    usuario = Usuario.query.get(session['usuario_id'])
    if usuario.role != 'admin_local':
        return redirect(url_for('admin.dashboard'))
    
    page = request.args.get('page', 1, type=int)
    per_page = 10
    estado = request.args.get('estado', 'pendiente')
    
    # Solo ver solicitudes de cursos de su institución
    query = SolicitudNuevoEstudiante.query.join(Curso).filter(
        Curso.institucion_id == usuario.institucion_id
    )
    
    if estado in ['pendiente', 'aprobado', 'rechazado']:
        query = query.filter(SolicitudNuevoEstudiante.estado == estado)
    
    total = query.count()
    solicitudes = query.order_by(
        SolicitudNuevoEstudiante.fecha_solicitud.desc()
    ).paginate(page=page, per_page=per_page, error_out=False).items
    
    total_pages = (total + per_page - 1) // per_page
    
    return render_template(
        'admin_local/solicitudes_nuevos_estudiantes.html',
        solicitudes=solicitudes,
        page=page,
        total_pages=total_pages,
        total=total,
        estado=estado,
        usuario=usuario
    )


@admin_bp.route('/solicitudes-nuevos-estudiantes/<int:solicitud_id>/aprobar', methods=['POST'])
@admin_required
def aprobar_nuevo_estudiante(solicitud_id):
    """Aprobar solicitud de nuevo estudiante (admin_local)"""
    try:
        usuario = Usuario.query.get(session['usuario_id'])
        if usuario.role != 'admin_local':
            return jsonify({'success': False, 'error': 'No tienes permiso'}), 403
        
        solicitud = SolicitudNuevoEstudiante.query.get(solicitud_id)
        if not solicitud or solicitud.estado != 'pendiente':
            return jsonify({'success': False, 'error': 'Solicitud inválida'}), 404
        
        # Verificar que la solicitud pertenece a la institución del admin
        if solicitud.curso.institucion_id != usuario.institucion_id:
            return jsonify({'success': False, 'error': 'No tienes permiso'}), 403
        
        # Verificar si el estudiante ya existe
        estudiante = Usuario.query.filter_by(email=solicitud.correo).first()
        
        if estudiante:
            # El estudiante ya existe, solo verificar que no esté inscrito en este curso
            existe_inscripcion = EstudianteCurso.query.filter_by(
                estudiante_id=estudiante.id,
                curso_id=solicitud.curso_id
            ).first()
            
            if existe_inscripcion:
                # Ya está inscrito en este curso, rechazar solicitud
                solicitud.estado = 'rechazado'
                solicitud.motivo_rechazo = 'Estudiante ya está inscrito en este curso'
                solicitud.admin_local_id = usuario.id
                solicitud.fecha_resolucion = datetime.utcnow()
                solicitud.estudiante_id = estudiante.id
                db.session.commit()
                return jsonify({
                    'success': False,
                    'error': 'Este estudiante ya está inscrito en este curso'
                }), 400
            else:
                # Inscribir estudiante en el nuevo curso
                inscripcion = EstudianteCurso(
                    estudiante_id=estudiante.id,
                    curso_id=solicitud.curso_id
                )
                db.session.add(inscripcion)
                
                solicitud.estado = 'aprobado'
                solicitud.admin_local_id = usuario.id
                solicitud.fecha_resolucion = datetime.utcnow()
                solicitud.estudiante_id = estudiante.id
                
                db.session.commit()
                
                return jsonify({
                    'success': True,
                    'mensaje': 'Estudiante inscrito en el curso'
                }), 200
        
        # El estudiante NO existe, crear nuevo usuario
        else:
            try:
                pwd_temporal = generar_contraseña_temporal()
                
                nuevo_estudiante = Usuario(
                    institucion_id=usuario.institucion_id,
                    email=solicitud.correo,
                    password=encriptar_contraseña(pwd_temporal),
                    nombre=solicitud.nombre,
                    apellido=solicitud.apellido,
                    role='estudiante',
                    estado='activo',
                    contraseña_cambiada=False  # Forzar cambio en primer login
                )
                
                db.session.add(nuevo_estudiante)
                db.session.flush()  # Para obtener el ID
                
                # Inscribir estudiante automáticamente en el curso
                inscripcion = EstudianteCurso(
                    estudiante_id=nuevo_estudiante.id,
                    curso_id=solicitud.curso_id
                )
                db.session.add(inscripcion)
                
                # Actualizar solicitud
                solicitud.estado = 'aprobado'
                solicitud.admin_local_id = usuario.id
                solicitud.fecha_resolucion = datetime.utcnow()
                solicitud.estudiante_id = nuevo_estudiante.id
                
                db.session.commit()
                
                return jsonify({
                    'success': True,
                    'mensaje': f'Estudiante creado e inscrito. Contraseña temporal: {pwd_temporal}'
                }), 200
                
            except Exception as e:
                db.session.rollback()
                raise e
        
    except Exception as e:
        db.session.rollback()
        print(f"[ERROR] Error al aprobar solicitud: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/solicitudes-nuevos-estudiantes/<int:solicitud_id>/rechazar', methods=['POST'])
@admin_required
def rechazar_nuevo_estudiante(solicitud_id):
    """Rechazar solicitud de nuevo estudiante (admin_local)"""
    try:
        usuario = Usuario.query.get(session['usuario_id'])
        if usuario.role != 'admin_local':
            return jsonify({'success': False, 'error': 'No tienes permiso'}), 403
        
        data = request.get_json()
        motivo = data.get('motivo', '').strip()
        
        solicitud = SolicitudNuevoEstudiante.query.get(solicitud_id)
        if not solicitud or solicitud.estado != 'pendiente':
            return jsonify({'success': False, 'error': 'Solicitud inválida'}), 404
        
        # Verificar que la solicitud pertenece a la institución del admin
        if solicitud.curso.institucion_id != usuario.institucion_id:
            return jsonify({'success': False, 'error': 'No tienes permiso'}), 403
        
        solicitud.estado = 'rechazado'
        solicitud.motivo_rechazo = motivo
        solicitud.admin_local_id = usuario.id
        solicitud.fecha_resolucion = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({'success': True, 'mensaje': 'Solicitud rechazada'}), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"[ERROR] Error al rechazar solicitud: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


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
        
        nombre = (request.form.get('nombre') or '').strip()
        ciudad = (request.form.get('ciudad') or '').strip()
        pais = (request.form.get('pais') or '').strip()

        if not all([nombre, ciudad, pais]):
            return jsonify({'success': False, 'error': 'Campos requeridos vacíos'}), 400

        if Institucion.query.filter_by(nombre=nombre).first():
            return jsonify({'success': False, 'error': 'Esta institución ya existe'}), 409

        nueva_inst = Institucion(nombre=nombre, ciudad=ciudad, pais=pais, activo=True)
        db.session.add(nueva_inst)
        db.session.flush()  # obtener el id antes del commit

        logo_file = request.files.get('logo')
        if logo_file and logo_file.filename:
            logo_fn = _save_logo(logo_file, nueva_inst.id)
            if logo_fn:
                nueva_inst.logo_filename = logo_fn

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
        
        nombre = (request.form.get('nombre') or institucion.nombre).strip()
        ciudad = (request.form.get('ciudad') or institucion.ciudad).strip()
        pais = (request.form.get('pais') or institucion.pais).strip()

        institucion.nombre = nombre
        institucion.ciudad = ciudad
        institucion.pais = pais

        logo_file = request.files.get('logo')
        if logo_file and logo_file.filename:
            logo_fn = _save_logo(logo_file, inst_id)
            if logo_fn:
                # eliminar logo anterior si existe y es diferente
                if institucion.logo_filename and institucion.logo_filename != logo_fn:
                    old_path = os.path.join(LOGOS_DIR, institucion.logo_filename)
                    if os.path.exists(old_path):
                        os.remove(old_path)
                institucion.logo_filename = logo_fn

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

@admin_bp.route('/simular-datos', methods=['POST'])
@admin_required
def simular_datos():
    """Crea actividades simuladas y calificaciones para todos los cursos activos sin actividades."""
    from models import Actividad, Calificacion, EstudianteCurso
    from datetime import datetime, timedelta
    from random import uniform, randint

    usuario = Usuario.query.get(session['usuario_id'])
    if usuario.role != 'admin_global':
        return jsonify({'success': False, 'error': 'Solo el admin global puede ejecutar esto'}), 403

    cursos = Curso.query.filter_by(activo=True).all()
    if not cursos:
        return jsonify({'success': False, 'error': 'No hay cursos activos'}), 400

    total_actividades = 0
    total_calificaciones = 0
    cursos_procesados = []
    cursos_saltados = []

    tipos = ['Taller', 'Parcial', 'Proyecto', 'Examen', 'Tarea']
    retroalimentaciones = [
        'Excelente trabajo. Siga así.',
        'Buen desempeño.',
        'Trabajo aceptable. Puede mejorar.',
        'Necesita más dedicación.',
        'Muy buena participación.',
        'Cumple con los requisitos mínimos.',
    ]

    try:
        for curso in cursos:
            if Actividad.query.filter_by(curso_id=curso.id).count() > 0:
                cursos_saltados.append(curso.codigo)
                continue

            fecha_inicio = curso.periodo.fecha_inicio if curso.periodo else datetime.now().date()
            estudiantes = (
                Usuario.query
                .join(EstudianteCurso)
                .filter(EstudianteCurso.curso_id == curso.id)
                .all()
            )

            for i in range(1, 10):
                tipo = tipos[i % len(tipos)]
                fecha_asig = fecha_inicio + timedelta(weeks=i * 2 - 2)
                fecha_venc = fecha_asig + timedelta(days=7)

                actividad = Actividad(
                    curso_id=curso.id,
                    nombre=f'{tipo} {i} - {curso.nombre}',
                    descripcion=f'Evaluación {tipo.lower()} número {i}',
                    tipo_evaluacion=tipo.lower(),
                    semana=i * 2,
                    ponderacion=round(1.0 / 9, 4),
                    fecha_asignacion=fecha_asig,
                    fecha_vencimiento=fecha_venc,
                    activa=True,
                )
                db.session.add(actividad)
                db.session.flush()
                total_actividades += 1

                for est in estudiantes:
                    nota = round(uniform(2.5, 5.0) if uniform(0, 1) >= 0.4 else uniform(3.8, 5.0), 1)
                    db.session.add(Calificacion(
                        actividad_id=actividad.id,
                        estudiante_id=est.id,
                        valor_nota=nota,
                        retroalimentacion=retroalimentaciones[randint(0, len(retroalimentaciones) - 1)],
                        fecha_calificacion=fecha_venc + timedelta(days=randint(1, 3)),
                    ))
                    total_calificaciones += 1

            cursos_procesados.append(curso.codigo)

        db.session.commit()
        return jsonify({
            'success': True,
            'actividades_creadas': total_actividades,
            'calificaciones_creadas': total_calificaciones,
            'cursos_procesados': cursos_procesados,
            'cursos_saltados': cursos_saltados,
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


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
