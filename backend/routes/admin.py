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
    """Cargar estudiantes desde CSV en una materia (admin_local)"""
    print(f"[DEBUG] Iniciando carga de estudiantes para curso_id: {curso_id}")
    
    try:
        # Validar sesión
        if 'usuario_id' not in session:
            print("[ERROR] No hay sesión activa")
            return jsonify({'success': False, 'error': 'Sesión expirada, inicia sesión de nuevo'}), 401
        
        usuario = Usuario.query.get(session['usuario_id'])
        if not usuario:
            print(f"[ERROR] Usuario no encontrado: {session['usuario_id']}")
            return jsonify({'success': False, 'error': 'Usuario no encontrado'}), 401
        
        print(f"[DEBUG] Usuario: {usuario.email}, Rol: {usuario.role}")
        
        if usuario.role != 'admin_local':
            print(f"[ERROR] Rol insuficiente: {usuario.role}")
            return jsonify({'success': False, 'error': 'Debes ser admin local para cargar estudiantes'}), 403

        # Validar curso
        curso = Curso.query.get(curso_id)
        if not curso:
            print(f"[ERROR] Curso no encontrado: {curso_id}")
            return jsonify({'success': False, 'error': 'Materia no encontrada'}), 404
        
        if curso.institucion_id != usuario.institucion_id:
            print(f"[ERROR] Institución no coincide. Curso: {curso.institucion_id}, Usuario: {usuario.institucion_id}")
            return jsonify({'success': False, 'error': 'No tienes permisos en esta materia'}), 403

        # Validar archivo
        print("[DEBUG] Validando archivo...")
        archivo = request.files.get('archivo')
        if not archivo:
            print("[ERROR] No se encontró archivo en la solicitud")
            return jsonify({'success': False, 'error': 'No se encontró archivo en la solicitud'}), 400
        
        if not archivo.filename:
            print("[ERROR] El archivo no tiene nombre")
            return jsonify({'success': False, 'error': 'El archivo no tiene nombre'}), 400
        
        if not archivo.filename.lower().endswith('.csv'):
            print(f"[ERROR] Archivo no es CSV: {archivo.filename}")
            return jsonify({'success': False, 'error': 'El archivo debe ser CSV'}), 400

        print(f"[DEBUG] Procesando archivo: {archivo.filename}")
        
        # Procesar CSV
        try:
            content = io.TextIOWrapper(archivo.stream, encoding='utf-8-sig')
            reader = csv.DictReader(content)
            
            if not reader.fieldnames:
                print("[ERROR] CSV vacío o sin columnas")
                return jsonify({'success': False, 'error': 'El CSV está vacío o no tiene columnas'}), 400
            
            fieldnames_lower = [n.strip().lower() for n in reader.fieldnames]
            print(f"[DEBUG] Columnas detectadas: {fieldnames_lower}")
            
            requeridos = {'email', 'nombre', 'apellido'}
            if not requeridos.issubset(set(fieldnames_lower)):
                print(f"[ERROR] Faltan columnas requeridas. Se encontraron: {fieldnames_lower}")
                return jsonify({
                    'success': False, 
                    'error': f'El CSV debe tener las columnas: email, nombre, apellido. Se encontraron: {", ".join(reader.fieldnames)}'
                }), 400

            creados = 0
            inscritos = 0
            omitidos = 0
            errores = 0
            vistos = set()
            errores_detalle = []

            for num_fila, row in enumerate(reader, start=2):  # start=2 porque fila 1 es header
                try:
                    email = (row.get('email') or '').strip().lower()
                    nombre = (row.get('nombre') or '').strip()
                    apellido = (row.get('apellido') or '').strip()

                    if not email or not nombre or not apellido:
                        errores += 1
                        errores_detalle.append(f"Fila {num_fila}: Faltan datos")
                        continue

                    if email in vistos:
                        omitidos += 1
                        continue
                    vistos.add(email)

                    es_valido, msg_error = validar_email(email)
                    if not es_valido:
                        errores += 1
                        errores_detalle.append(f"Fila {num_fila}: Email inválido ({email})")
                        continue

                    estudiante = Usuario.query.filter_by(email=email).first()
                    if estudiante:
                        if estudiante.role != 'estudiante' or estudiante.institucion_id != usuario.institucion_id:
                            errores += 1
                            errores_detalle.append(f"Fila {num_fila}: Usuario existe pero no es estudiante o es de otra institución")
                            continue
                    else:
                        estudiante = Usuario(
                            institucion_id=usuario.institucion_id,
                            email=email,
                            password=encriptar_contraseña('Estudiante123!'),
                            nombre=nombre,
                            apellido=apellido,
                            role='estudiante',
                            estado='activo'
                        )
                        db.session.add(estudiante)
                        db.session.flush()
                        creados += 1

                    existe = EstudianteCurso.query.filter_by(
                        estudiante_id=estudiante.id,
                        curso_id=curso.id
                    ).first()
                    if existe:
                        omitidos += 1
                        continue

                    db.session.add(EstudianteCurso(
                        estudiante_id=estudiante.id,
                        curso_id=curso.id
                    ))
                    inscritos += 1
                
                except Exception as e_fila:
                    errores += 1
                    errores_detalle.append(f"Fila {num_fila}: {str(e_fila)}")
                    print(f"[ERROR] Fila {num_fila}: {e_fila}")

            db.session.commit()
            
            print(f"[SUCCESS] Carga completada. Creados: {creados}, Inscritos: {inscritos}, Omitidos: {omitidos}, Errores: {errores}")
            
            mensaje = f'✅ Carga finalizada.\n✓ Creados: {creados}\n✓ Inscritos: {inscritos}\n↷ Omitidos: {omitidos}'
            if errores > 0:
                mensaje += f'\n✗ Errores: {errores}'
            
            return jsonify({
                'success': True,
                'mensaje': mensaje,
                'creados': creados,
                'inscritos': inscritos,
                'omitidos': omitidos,
                'errores': errores
            }), 200

        except csv.Error as e_csv:
            print(f"[ERROR] Error al procesar CSV: {e_csv}")
            return jsonify({'success': False, 'error': f'Error al procesar CSV: {str(e_csv)}'}), 400

    except Exception as e:
        db.session.rollback()
        print(f"[ERROR] Error general al cargar estudiantes: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False, 
            'error': f'Error interno: {type(e).__name__}: {str(e)}'
        }), 500

# ============================================================================
# RUTA: ACTUALIZAR CURSO (AJAX)
# ============================================================================

@admin_bp.route('/cursos/<int:curso_id>/actualizar', methods=['POST'])
@admin_required
def actualizar_curso(curso_id):
    """Actualizar curso existente"""
    try:
        data = request.get_json()
        
        curso = Curso.query.get(curso_id)
        if not curso:
            return jsonify({'success': False, 'error': 'Curso no encontrado'}), 404
        
        usuario = Usuario.query.get(session['usuario_id'])
        if usuario.role == 'admin_local' and usuario.institucion_id != curso.institucion_id:
            return jsonify({'success': False, 'error': 'No tienes permiso'}), 403

        institucion_id = curso.institucion_id
        institucion_id_nueva = data.get('institucion_id')
        if usuario.role == 'admin_global' and institucion_id_nueva is not None:
            try:
                institucion_id_nueva = int(institucion_id_nueva)
            except (TypeError, ValueError):
                return jsonify({'success': False, 'error': 'Institución inválida'}), 400

            institucion = Institucion.query.get(institucion_id_nueva)
            if not institucion or not institucion.activo:
                return jsonify({'success': False, 'error': 'Institución no disponible'}), 404
            institucion_id = institucion.id
        
        periodo_nombre = data.get('periodo_nombre', '').strip()
        fecha_inicio = data.get('fecha_inicio', '').strip()
        fecha_fin = data.get('fecha_fin', '').strip()

        # Actualizar campos
        curso.nombre = data.get('nombre', curso.nombre).strip()
        curso.codigo = data.get('codigo', curso.codigo).strip()
        curso.creditos = data.get('creditos', curso.creditos)
        curso.descripcion = data.get('descripcion', curso.descripcion).strip()
        # Actualizar dias de clase y sesiones por semana si vienen
        dias_semana = data.get('dias_semana')
        sesiones_por_semana = data.get('sesiones_por_semana')
        if dias_semana is not None:
            curso.dias_semana = dias_semana or None
        if sesiones_por_semana is not None:
            try:
                curso.sesiones_por_semana = int(sesiones_por_semana)
            except (TypeError, ValueError):
                curso.sesiones_por_semana = 0

        curso.institucion_id = institucion_id
        docente_principal_id = data.get('docente_principal_id', curso.docente_principal_id)
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

            if docente_principal.institucion_id != institucion_id:
                return jsonify({'success': False, 'error': 'Docente no disponible'}), 400

            curso.docente_principal_id = docente_principal.id
        else:
            curso.docente_principal_id = None

        if periodo_nombre and fecha_inicio and fecha_fin:
            try:
                inicio = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
                fin = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'success': False, 'error': 'Fechas inválidas'}), 400

            if fin < inicio:
                return jsonify({'success': False, 'error': 'La fecha fin debe ser mayor a la fecha inicio'}), 400

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
                db.session.add(periodo)
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
