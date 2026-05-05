"""Utilidades para validación y seguridad"""
import re
from werkzeug.security import generate_password_hash, check_password_hash

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
