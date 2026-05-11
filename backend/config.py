"""Configuración de la aplicación Flask"""
import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Configuración base"""
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    SESSION_COOKIE_SECURE = False  # Cambiar a True si usas HTTPS en producción
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

class DevelopmentConfig(Config):
    """Configuración para desarrollo"""
    DEBUG = True
    SQLALCHEMY_ECHO = False
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL', 
        'sqlite:///app.db'
    )

class ProductionConfig(Config):
    """Configuración para producción"""
    DEBUG = False
    # En Render, DATABASE_URL viene automáticamente cuando agregues PostgreSQL
    db_url = os.getenv(
        'DATABASE_URL',
        'postgresql://user:password@localhost:5432/academico'
    )
    SQLALCHEMY_DATABASE_URI = db_url
    
    # Configuración para PostgreSQL con SSL en Render
    if 'postgresql' in db_url:
        SQLALCHEMY_ENGINE_OPTIONS = {
            'connect_args': {
                'sslmode': 'require',
            },
            'pool_pre_ping': True,      # Verificar conexión antes de usar
            'pool_recycle': 3600,       # Reciclar conexiones cada hora
            'pool_size': 10,
            'max_overflow': 20,
        }
    
    # Cookies seguras en HTTPS
    SESSION_COOKIE_SECURE = True

class TestingConfig(Config):
    """Configuración para testing"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

# Diccionario con configuraciones
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
