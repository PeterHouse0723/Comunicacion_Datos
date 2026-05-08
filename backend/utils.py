"""Utilidades para validación y seguridad"""
import re
from werkzeug.security import generate_password_hash, check_password_hash
import secrets
import string
from datetime import datetime, timedelta

def validar_contraseña(contraseña):
    """
    Valida que la contraseña cumpla con los requisitos:
    - Mínimo 8 caracteres
    - Al menos 1 mayúscula
    - Al menos 1 número
    - Al menos 1 carácter especial (!@#$%^&*)
    
    Returns: (bool, str) - (es_válida, mensaje_error)
    """
    if len(contraseña) < 8:
        return False, "La contraseña debe tener mínimo 8 caracteres"
    
    if not re.search(r'[A-Z]', contraseña):
        return False, "La contraseña debe contener al menos 1 mayúscula"
    
    if not re.search(r'[0-9]', contraseña):
        return False, "La contraseña debe contener al menos 1 número"
    
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', contraseña):
        return False, "La contraseña debe contener al menos 1 carácter especial (!@#$%^&*)"
    
    return True, "Contraseña válida"

def encriptar_contraseña(contraseña):
    """
    Encripta una contraseña usando Werkzeug (bcrypt interno)
    
    Args: contraseña (str)
    Returns: str - Hash encriptado
    """
    return generate_password_hash(contraseña, method='pbkdf2:sha256')

def verificar_contraseña(contraseña_ingresada, hash_almacenado):
    """
    Verifica que la contraseña ingresada coincida con el hash almacenado
    
    Args:
        contraseña_ingresada (str): Contraseña que el usuario ingresa
        hash_almacenado (str): Hash guardado en la BD
    
    Returns: bool - True si coincide, False si no
    """
    return check_password_hash(hash_almacenado, contraseña_ingresada)

def validar_email(email):
    """
    Valida que el email tenga un formato correcto
    
    Args: email (str)
    Returns: (bool, str) - (es_válido, mensaje)
    """
    patron = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if not re.match(patron, email):
        return False, "Email inválido"
    
    return True, "Email válido"

def generar_contraseña_temporal():
    """
    Genera una contraseña temporal que cumple con los requisitos
    Formato: Temp + número + carácter especial + letras
    Ejemplo: Temp123!abc
    
    Returns: str - Contraseña temporal
    """
    caracteres_especiales = "!@#$%^&*()"
    letras_mayus = string.ascii_uppercase
    letras_minus = string.ascii_lowercase
    numeros = string.digits
    
    # Garantizar que incluya: 1 mayúscula, 1 número, 1 especial
    contraseña = [
        secrets.choice(letras_mayus),
        secrets.choice(numeros),
        secrets.choice(caracteres_especiales),
        secrets.choice(letras_minus),
        secrets.choice(letras_minus),
        secrets.choice(letras_minus),
        secrets.choice(letras_minus),
    ]
    
    # Mezclar y retornar
    secrets.SystemRandom().shuffle(contraseña)
    return ''.join(contraseña)

def generar_token_reset(longitud=32):
    """
    Genera un token seguro para reset de contraseña
    
    Args: longitud (int) - Longitud del token en caracteres
    Returns: str - Token hexadecimal aleatorio
    """
    return secrets.token_urlsafe(longitud)

def validar_token_reset(token_str, expiracion_token):
    """
    Valida que el token de reset no haya expirado
    
    Args:
        token_str (str): Token a validar
        expiracion_token (datetime): Fecha de expiración del token
    
    Returns: bool - True si es válido, False si expiró
    """
    if not token_str or not expiracion_token:
        return False
    
    return datetime.utcnow() < expiracion_token

def generar_expiracion_token(minutos=30):
    """
    Genera una fecha de expiración para un token
    
    Args: minutos (int) - Minutos hasta expiración (default 30 minutos)
    Returns: datetime - Fecha de expiración
    """
    return datetime.utcnow() + timedelta(minutes=minutos)

def crear_usuario_con_contraseña_temporal(db, Usuario, email, nombre, apellido, institucion_id, role='estudiante', contraseña_inicial='Peter0723@'):
    """
    Crea un usuario con la clave inicial compartida para estudiantes
    
    Args:
        db: SQLAlchemy database instance
        Usuario: Modelo de Usuario
        email (str): Email del usuario
        nombre (str): Nombre del usuario
        apellido (str): Apellido del usuario
        institucion_id (int): ID de la institución
        role (str): Rol del usuario (default 'estudiante')
    
    Returns: tuple (usuario, contraseña_inicial) o (None, mensaje_error)
    """
    # Verificar que el email no exista
    if Usuario.query.filter_by(email=email).first():
        return None, f"El email {email} ya está registrado"
    
    try:
        nuevo_usuario = Usuario(
            institucion_id=institucion_id,
            email=email,
            password=encriptar_contraseña(contraseña_inicial),
            nombre=nombre,
            apellido=apellido,
            role=role,
            estado='activo'
        )
        db.session.add(nuevo_usuario)
        db.session.commit()
        
        return nuevo_usuario, contraseña_inicial
    
    except Exception as e:
        db.session.rollback()
        return None, f"Error al crear usuario: {str(e)}"
