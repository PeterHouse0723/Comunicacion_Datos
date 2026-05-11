#!/usr/bin/env python
"""
Script de gestión para la aplicación Flask
Maneja migraciones y tareas de base de datos
"""
import os
import sys
from flask_script import Manager
from flask_migrate import Migrate, MigrateCommand
from app import create_app, db
from models import (
    Institucion, Usuario, Periodo, Curso, CursoDocente, EstudianteCurso,
    SolicitudEstudianteMateria, Clase, Nota, Asistencia, AlertaRiesgoAcademico,
    LoginAuditoria, Notificacion
)

# Usar la configuración de ambiente
config_name = os.getenv('FLASK_ENV', 'development')
app = create_app(config_name=config_name)
migrate = Migrate(app, db)

manager = Manager(app)
manager.add_command('db', MigrateCommand)

@manager.command
def migrate_db():
    """Ejecuta las migraciones de base de datos"""
    print("Ejecutando migraciones...")
    os.system('flask db upgrade')
    print("✓ Migraciones completadas")

@manager.command
def init_db():
    """Inicializa la base de datos con datos por defecto"""
    print("Inicializando base de datos...")
    with app.app_context():
        db.create_all()
        print("✓ Tablas creadas")
        
        # Crear institución por defecto
        if not Institucion.query.first():
            institucion = Institucion(
                nombre='Universidad Default',
                ciudad='Bogotá',
                pais='Colombia',
                activo=True
            )
            db.session.add(institucion)
            db.session.commit()
            print("✓ Institución creada")

@manager.command
def create_admin():
    """Crea un usuario administrador por defecto"""
    from utils import encriptar_contraseña
    
    with app.app_context():
        institucion = Institucion.query.first()
        if not institucion:
            print("❌ No existe institución. Ejecuta 'python manage.py init_db' primero")
            return
        
        if not Usuario.query.filter_by(email='admin@universitario.edu').first():
            admin = Usuario(
                institucion_id=institucion.id,
                email='admin@universitario.edu',
                password=encriptar_contraseña('Admin123!'),
                nombre='Administrador',
                apellido='Global',
                role='admin_global',
                estado='activo'
            )
            db.session.add(admin)
            db.session.commit()
            print("✓ Admin creado: admin@universitario.edu / Admin123!")
        else:
            print("ℹ Admin ya existe")

if __name__ == '__main__':
    manager.run()
