from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session
from app import db
from models import Usuario, Role, LoginAuditoria
from utils import validar_contraseña, encriptar_contraseña, validar_email

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')
    
    # POST: Procesar login
    email = request.form.get('email')
    password = request.form.get('password')
    
    # Validar que no sean vacíos
    if not email or not password:
        return render_template('login.html', error='Email y contraseña son requeridos'), 400
    
    # Buscar usuario
    usuario = Usuario.query.filter_by(email=email).first()
    
    if usuario:
        # TODO: Implementar verificación de contraseña
        # Por ahora es placeholder
        pass
    
    # Registrar intento en auditoría (exitoso o fallido)
    # TODO: Implementar registro de auditoría
    
    return {'status': 'pendiente implementación'}


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('register.html')
    
    # POST: Procesar registro
    nombre = request.form.get('nombre')
    apellido = request.form.get('apellido')
    email = request.form.get('email')
    rol = request.form.get('rol')
    password = request.form.get('password')
    confirm_password = request.form.get('confirm_password')
    
    # VALIDACIONES
    # 1. Verificar que no falten campos
    if not all([nombre, apellido, email, rol, password, confirm_password]):
        return jsonify({'error': 'Todos los campos son requeridos'}), 400
    
    # 2. Validar email
    es_valido, mensaje = validar_email(email)
    if not es_valido:
        return jsonify({'error': mensaje}), 400
    
    # 3. Verificar que email no exista
    if Usuario.query.filter_by(email=email).first():
        return jsonify({'error': 'El email ya está registrado'}), 409
    
    # 4. Validar contraseña
    es_valida, mensaje = validar_contraseña(password)
    if not es_valida:
        return jsonify({'error': mensaje}), 400
    
    # 5. Verificar que coincidan las contraseñas
    if password != confirm_password:
        return jsonify({'error': 'Las contraseñas no coinciden'}), 400
    
    # 6. Verificar que el rol sea válido
    if rol not in ['estudiante', 'docente']:
        return jsonify({'error': 'Rol inválido'}), 400
    
    try:
        # Obtener role_id
        role = Role.query.filter_by(nombre=rol).first()
        if not role:
            return jsonify({'error': 'Rol no encontrado en sistema'}), 500
        
        # Crear nuevo usuario
        nuevo_usuario = Usuario(
            email=email,
            password=encriptar_contraseña(password),
            nombre=nombre,
            apellido=apellido,
            role_id=role.id,
            activo=True
        )
        
        # Guardar en BD
        db.session.add(nuevo_usuario)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'mensaje': 'Usuario registrado exitosamente',
            'redirect': url_for('auth.login')
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error al registrar: {str(e)}'}), 500
