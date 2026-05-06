"""Rutas administrativas - Admin Global"""
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session
from extensions import db
from models import Usuario, Institucion, Curso, Periodo, CursoDocente
from utils import validar_email, validar_contraseña, encriptar_contraseña, verificar_contraseña
from functools import wraps
from datetime import datetime
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
            return redirect(url_for('dashboard.index'))
        
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
        instituciones_count = Institucion.query.filter_by(activo=True).count()
        cursos_count = Curso.query.filter_by(activo=True).count()

        stats = {
            'docentes_pendientes': docentes_pendientes,
            'instituciones': instituciones_count,
            'cursos': cursos_count,
            'usuarios': Usuario.query.count()
        }
    
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
    
    return render_template('admin/docentes_pendientes.html', 
                          docentes=docentes, 
                          page=page, 
                          total_pages=total_pages,
                          total=total)

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
    
    usuario = Usuario.query.get(session['usuario_id'])
    
    # Si es admin_local, solo ver su institución
    if usuario.role == 'admin_local':
        query = Curso.query.filter_by(institucion_id=usuario.institucion_id)
    else:
        query = Curso.query
    
    total = query.count()
    cursos_list = query.paginate(page=page, per_page=per_page, error_out=False).items
    
    total_pages = math.ceil(total / per_page)
    
    # Obtener períodos activos para el form
    periodos = Periodo.query.filter_by(activo=True).all()
    
    # Obtener docentes disponibles
    docentes = Usuario.query.filter_by(role='docente', estado='activo').all()
    
    return render_template('admin/cursos.html',
                          cursos=cursos_list,
                          page=page,
                          total_pages=total_pages,
                          total=total,
                          periodos=periodos,
                          docentes=docentes)

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
        creditos = data.get('creditos', 3)
        descripcion = data.get('descripcion', '').strip()
        
        if not all([nombre, codigo, periodo_nombre, fecha_inicio, fecha_fin]):
            return jsonify({'success': False, 'error': 'Campos requeridos vacíos'}), 400

        try:
            inicio = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
            fin = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'success': False, 'error': 'Fechas inválidas'}), 400

        if fin < inicio:
            return jsonify({'success': False, 'error': 'La fecha fin debe ser mayor a la fecha inicio'}), 400

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
        
        # Crear curso
        nuevo_curso = Curso(
            institucion_id=institucion_id,
            periodo_id=periodo.id,
            nombre=nombre,
            codigo=codigo,
            creditos=creditos,
            descripcion=descripcion,
            docente_principal_id=docente_principal_id,
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
        
        periodo_nombre = data.get('periodo_nombre', '').strip()
        fecha_inicio = data.get('fecha_inicio', '').strip()
        fecha_fin = data.get('fecha_fin', '').strip()

        # Actualizar campos
        curso.nombre = data.get('nombre', curso.nombre).strip()
        curso.codigo = data.get('codigo', curso.codigo).strip()
        curso.creditos = data.get('creditos', curso.creditos)
        curso.descripcion = data.get('descripcion', curso.descripcion).strip()
        curso.docente_principal_id = data.get('docente_principal_id', curso.docente_principal_id)

        if periodo_nombre and fecha_inicio and fecha_fin:
            try:
                inicio = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
                fin = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'success': False, 'error': 'Fechas inválidas'}), 400

            if fin < inicio:
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
