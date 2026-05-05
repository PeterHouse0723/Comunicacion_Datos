"""Rutas de autenticación - Login y Registro"""
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session
from extensions import db
from models import Usuario, LoginAuditoria, Institucion
from utils import validar_contraseña, encriptar_contraseña, verificar_contraseña, validar_email
from functools import wraps
import os

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

# ============================================================================
# DECORADOR: Verificar sesión activa
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
# RUTA: LOGIN
# ============================================================================

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    GET: Muestra formulario de login
    POST: Procesa login del usuario
    """
    if request.method == 'GET':
        # Si ya está logueado, redirigir al dashboard según su rol
        if 'usuario_id' in session:
            rol = session.get('role')
            if rol in ['admin_global', 'admin_local']:
                return redirect(url_for('dashboard.admin'))
            elif rol == 'docente':
                return redirect(url_for('dashboard.docente'))
            elif rol == 'estudiante':
                return redirect(url_for('dashboard.estudiante'))
        
        return render_template('login.html')
    
    # POST: Procesar login
    email = request.form.get('email', '').strip()
    password = request.form.get('password', '')
    
    # Validaciones
    if not email or not password:
        return render_template('login.html', error='Email y contraseña son requeridos'), 400
    
    # Buscar usuario por email
    usuario = Usuario.query.filter_by(email=email).first()
    
    if not usuario:
        return render_template('login.html', error='Email o contraseña incorrectos'), 401
    
    # Verificar contraseña
    if not verificar_contraseña(password, usuario.password):
        return render_template('login.html', error='Email o contraseña incorrectos'), 401
    
    # Verificar que el usuario esté activo
    if usuario.estado != 'activo':
        estado_msg = {
            'pendiente': 'Tu cuenta está pendiente de aprobación por el administrador',
            'inactivo': 'Tu cuenta está inactiva',
            'suspendido': 'Tu cuenta ha sido suspendida'
        }
        return render_template('login.html', error=estado_msg.get(usuario.estado, 'Cuenta no disponible')), 403
    
    # Obtener IP del cliente
    ip_client = request.remote_addr or request.environ.get('HTTP_X_FORWARDED_FOR', 'desconocida')
    navegador = request.user_agent.string
    
    try:
        # Registrar en auditoría (login exitoso)
        auditoria = LoginAuditoria(
            usuario_id=usuario.id,
            ip_address=ip_client,
            navegador=navegador,
            estado='exitoso'
        )
        db.session.add(auditoria)
        db.session.commit()
    except Exception as e:
        print(f"[WARN] Error al registrar auditoria: {e}")
        # Continuamos aunque falle la auditoria
    
    # Crear sesión
    session['usuario_id'] = usuario.id
    session['email'] = usuario.email
    session['nombre'] = usuario.nombre
    session['role'] = usuario.role
    session.permanent = True
    
    print(f"[OK] Login exitoso para {usuario.email} ({usuario.role})")
    
    # Redirigir según rol
    if usuario.role == 'admin_global' or usuario.role == 'admin_local':
        return redirect(url_for('dashboard.admin'))
    elif usuario.role == 'docente':
        return redirect(url_for('dashboard.docente'))
    elif usuario.role == 'estudiante':
        return redirect(url_for('dashboard.estudiante'))
    
    return redirect(url_for('auth.login'))

# ============================================================================
# RUTA: LOGOUT
# ============================================================================

@auth_bp.route('/logout')
def logout():
    """Cierra la sesión del usuario"""
    session.clear()
    return redirect(url_for('auth.login'))

# ============================================================================
# RUTA: REGISTER
# ============================================================================

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """
    GET: Muestra formulario de registro
    POST: Procesa registro del usuario
    """
    try:
        print(f"[ROUTE] /register accessed - Method: {request.method}")
        
        if request.method == 'GET':
            # Obtener instituciones para que elijan
            instituciones = Institucion.query.filter_by(activo=True).all()
            
            return render_template('register.html', instituciones=instituciones)
        
        # POST: Procesar registro
        print(f"[INFO] Procesando registration POST request")
        nombre = request.form.get('nombre', '').strip()
        apellido = request.form.get('apellido', '').strip()
        email = request.form.get('email', '').strip()
        rol = request.form.get('rol', 'estudiante').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        institucion_id = request.form.get('institucion_id')
        
        # ==================== VALIDACIONES ====================
        
        # 1. Verificar que no falten campos
        if not all([nombre, apellido, email, password, confirm_password]):
            return jsonify({
                'success': False,
                'error': 'Todos los campos son requeridos'
            }), 400
        
        # 2. Validar que rol sea válido
        if rol not in ['estudiante', 'docente']:
            return jsonify({
                'success': False,
                'error': 'Rol inválido'
            }), 400
        
        # 3. Validar email
        es_valido, mensaje = validar_email(email)
        if not es_valido:
            return jsonify({
                'success': False,
                'error': mensaje
            }), 400
        
        # 4. Verificar que email no exista
        if Usuario.query.filter_by(email=email).first():
            return jsonify({
                'success': False,
                'error': 'El email ya está registrado'
            }), 409
        
        # 5. Validar contraseña
        es_valida, mensaje = validar_contraseña(password)
        if not es_valida:
            return jsonify({
                'success': False,
                'error': mensaje
            }), 400
        
        # 6. Verificar que coincidan las contraseñas
        if password != confirm_password:
            return jsonify({
                'success': False,
                'error': 'Las contraseñas no coinciden'
            }), 400
        
        # 7. Validar institución
        try:
            institucion_id = int(institucion_id) if institucion_id else None
        except (ValueError, TypeError):
            return jsonify({
                'success': False,
                'error': 'Institución inválida'
            }), 400
        
        institucion = Institucion.query.filter_by(id=institucion_id, activo=True).first()
        if not institucion:
            return jsonify({
                'success': False,
                'error': 'Institución inválida'
            }), 400
        
        # ==================== CREAR USUARIO ====================
        
        nuevo_usuario = Usuario(
            institucion_id=institucion.id,
            email=email,
            password=encriptar_contraseña(password),
            nombre=nombre,
            apellido=apellido,
            role=rol,
            # Si es docente: pendiente de aprobación
            # Si es estudiante: activo inmediatamente
            estado='pendiente' if rol == 'docente' else 'activo'
        )
        
        db.session.add(nuevo_usuario)
        db.session.commit()
        
        print(f"[OK] Usuario registrado: {email} ({rol})")
        
        # Retornar JSON para AJAX
        return jsonify({
            'success': True,
            'mensaje': 'Registro exitoso. Redirigiendo...'
        }), 201
    
    except Exception as e:
        db.session.rollback()
        print(f"[ERROR] Error en register(): {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return jsonify({
            'success': False,
            'error': f'Error: {str(e)}'
        }), 500
