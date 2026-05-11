#!/usr/bin/env python
"""
Script de verificación pre-deployment
Valida que el proyecto esté listo para Render
"""
import os
import sys
import subprocess
from pathlib import Path

def print_header(message):
    print(f"\n{'='*60}")
    print(f"  {message}")
    print(f"{'='*60}\n")

def print_success(message):
    print(f"✅ {message}")

def print_error(message):
    print(f"❌ {message}")

def print_warning(message):
    print(f"⚠️  {message}")

def check_files_exist():
    """Verifica que los archivos necesarios existan"""
    print_header("1. VERIFICANDO ARCHIVOS NECESARIOS")
    
    required_files = [
        'app.py',
        'wsgi.py',
        'config.py',
        'requirements.txt',
        'manage.py',
        'Procfile',
        '.env.example',
        'models.py',
        'extensions.py',
    ]
    
    missing = []
    for file in required_files:
        if os.path.exists(file):
            print_success(f"{file}")
        else:
            print_error(f"{file} - FALTA")
            missing.append(file)
    
    return len(missing) == 0

def check_requirements():
    """Verifica dependencias en requirements.txt"""
    print_header("2. VERIFICANDO DEPENDENCIAS")
    
    required_packages = [
        'Flask',
        'Flask-SQLAlchemy',
        'Flask-Migrate',
        'psycopg2-binary',
        'python-dotenv',
        'gunicorn',
    ]
    
    try:
        with open('requirements.txt', 'r') as f:
            content = f.read()
        
        missing = []
        for pkg in required_packages:
            if pkg.lower() in content.lower():
                print_success(f"{pkg}")
            else:
                print_error(f"{pkg} - FALTA EN requirements.txt")
                missing.append(pkg)
        
        return len(missing) == 0
    except FileNotFoundError:
        print_error("requirements.txt no encontrado")
        return False

def check_config():
    """Verifica que config.py tenga las configuraciones necesarias"""
    print_header("3. VERIFICANDO CONFIGURACIÓN")
    
    try:
        with open('config.py', 'r') as f:
            content = f.read()
        
        checks = {
            'ProductionConfig': 'Clase ProductionConfig',
            'DATABASE_URL': 'Variable DATABASE_URL',
            'DEBUG = False': 'Debug deshabilitado en producción',
        }
        
        missing = []
        for check, description in checks.items():
            if check in content:
                print_success(description)
            else:
                print_warning(f"{description} - REVISAR")
                missing.append(check)
        
        return len(missing) <= 1  # Toleramos 1 falta
    except FileNotFoundError:
        print_error("config.py no encontrado")
        return False

def check_env_file():
    """Verifica si existe .env.example"""
    print_header("4. VERIFICANDO .env.example")
    
    if os.path.exists('.env.example'):
        print_success(".env.example existe")
        with open('.env.example', 'r') as f:
            content = f.read()
            if 'DATABASE_URL' in content:
                print_success("DATABASE_URL documentada")
                return True
            else:
                print_error("DATABASE_URL no documentada en .env.example")
                return False
    else:
        print_error(".env.example no encontrado")
        return False

def check_git():
    """Verifica que el proyecto esté en Git"""
    print_header("5. VERIFICANDO GIT")
    
    try:
        result = subprocess.run(['git', 'status'], capture_output=True, text=True)
        if result.returncode == 0:
            print_success("Repositorio Git configurado")
            
            # Verificar si hay cambios sin hacer commit
            result = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True)
            if result.stdout:
                print_warning("Hay cambios sin hacer commit")
                return True
            else:
                print_success("Todos los cambios están en Git")
                return True
        else:
            print_error("Git no está inicializado. Ejecuta: git init")
            return False
    except FileNotFoundError:
        print_error("Git no está instalado")
        return False

def check_imports():
    """Verifica que los módulos principales se puedan importar"""
    print_header("6. VERIFICANDO IMPORTS DE PYTHON")
    
    try:
        import flask
        print_success("Flask importable")
        
        import sqlalchemy
        print_success("SQLAlchemy importable")
        
        import psycopg2
        print_success("psycopg2 importable")
        
        return True
    except ImportError as e:
        print_warning(f"Módulo no encontrado: {e}")
        print("Sugerencia: ejecuta 'pip install -r requirements.txt'")
        return False

def check_port():
    """Verifica que el puerto 5000 esté disponible"""
    print_header("7. VERIFICANDO PUERTO 5000")
    
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', 5000))
        sock.close()
        
        if result == 0:
            print_warning("Puerto 5000 ya está en uso")
            return False
        else:
            print_success("Puerto 5000 disponible")
            return True
    except Exception as e:
        print_warning(f"No se pudo verificar puerto: {e}")
        return True

def main():
    print("\n" + "="*60)
    print("  🔍 VERIFICADOR PRE-DEPLOYMENT PARA RENDER")
    print("="*60)
    
    checks = [
        ("Archivos necesarios", check_files_exist()),
        ("Dependencias", check_requirements()),
        ("Configuración", check_config()),
        (".env.example", check_env_file()),
        ("Git", check_git()),
        ("Imports de Python", check_imports()),
        ("Puerto 5000", check_port()),
    ]
    
    print_header("RESUMEN")
    
    passed = sum(1 for _, result in checks if result)
    total = len(checks)
    
    for check_name, result in checks:
        status = "✅" if result else "❌"
        print(f"{status} {check_name}")
    
    print(f"\nTotal: {passed}/{total} verificaciones pasadas")
    
    if passed == total:
        print_success("\n¡Todo está listo para Render!\n")
        return 0
    else:
        print_error(f"\nFaltan {total - passed} verificaciones\n")
        return 1

if __name__ == '__main__':
    sys.exit(main())
