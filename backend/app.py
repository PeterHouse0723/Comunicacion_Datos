from flask import Flask, render_template, redirect, url_for
from extensions import db, migrate
from config import config
from utils import encriptar_contraseña
import os
from sqlalchemy import text
import logging

# Configurar logging
logger = logging.getLogger(__name__)

# Importar modelos después de que db esté disponible
from models import (
    Institucion, Usuario, Periodo, Curso, CursoDocente, EstudianteCurso,
    SolicitudEstudianteMateria, SolicitudNuevoEstudiante, Clase, Nota, Asistencia, AlertaRiesgoAcademico,
    LoginAuditoria, Notificacion, Mensaje, AlertaBienestar
)

def apply_migrations(app):
    """Aplica las migraciones SQL desde el directorio migrations/"""
    migrations_dir = os.path.join(os.path.dirname(__file__), 'migrations')
    migration_files = [
        'add_authentication_fields.sql',
        'add_contraseña_cambiada.sql',
        'create_solicitudes_nuevo_estudiante.sql',
        'create_mensajes.sql',
        'add_institucion_logo.sql',
        'create_actividades.sql',
        'create_calificaciones.sql',
        'create_actividades_apoyo.sql',
        'add_archivo_apoyo.sql',
        'add_hora_cierre_apoyo.sql',
        'add_calificacion_reemplazo_apoyo.sql',
        'create_alertas_bienestar.sql',
    ]
    
    for migration_file in migration_files:
        migration_path = os.path.join(migrations_dir, migration_file)
        if os.path.exists(migration_path):
            try:
                with open(migration_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Dividir por ; y ejecutar cada comando por separado
                commands = content.split(';')
                
                db_url = app.config.get('SQLALCHEMY_DATABASE_URI', '')
                is_sqlite = 'sqlite' in db_url

                for command in commands:
                    # Limpiar comentarios y espacios en blanco
                    lines = []
                    for line in command.split('\n'):
                        if '--' in line:
                            line = line[:line.index('--')]
                        line = line.strip()
                        if line:
                            lines.append(line)

                    sql_command = ' '.join(lines)

                    # SQLite no soporta "ADD COLUMN IF NOT EXISTS" — eliminar la cláusula
                    if is_sqlite:
                        import re
                        sql_command = re.sub(
                            r'ADD COLUMN IF NOT EXISTS',
                            'ADD COLUMN',
                            sql_command,
                            flags=re.IGNORECASE
                        )

                    # Ignorar comandos vacíos y COMMIT
                    if sql_command and sql_command.upper() != 'COMMIT':
                        try:
                            db.session.execute(text(sql_command))
                        except Exception as e:
                            # Algunos comandos pueden fallar si ya existen (esperado)
                            err = str(e).lower()
                            if ('already exists' in err or 'does not exist' in err
                                    or 'already has column' in err or 'duplicate column' in err):
                                logger.debug(f"Migration note: {str(e)}")
                            else:
                                raise
                
                db.session.commit()
                logger.info(f"✓ Migración aplicada: {migration_file}")
                
            except Exception as e:
                logger.error(f"✗ Error en migración {migration_file}: {str(e)}")
                db.session.rollback()
                raise
        else:
            logger.warning(f"Archivo de migración no encontrado: {migration_file}")

def create_app(config_name=None):
    """Factory para crear la aplicación Flask"""
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')
    
    app = Flask(__name__, template_folder='templates', static_folder='static')
    app.config.from_object(config[config_name])
    
    # Inicializar extensiones
    db.init_app(app)
    migrate.init_app(app, db)
    
    # Registrar blueprints (rutas)
    from routes.auth import auth_bp
    from routes.dashboard import dashboard_bp
    from routes.admin import admin_bp
    from chatbot.routes import chatbot_bp
    from routes.pro_lineal import pro_lineal_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(chatbot_bp)
    app.register_blueprint(pro_lineal_bp)
    
    # Inicializar base de datos y aplicar migraciones
    with app.app_context():
        try:
            # Aplicar migraciones SQL (SIEMPRE, incluso en producción)
            apply_migrations(app)
        except Exception as e:
            logger.error(f"Error al aplicar migraciones: {e}")
            # No fallar si las migraciones no se pueden aplicar, solo loguear
        
        # Crear tablas si no existen (solo en desarrollo)
        if config_name != 'production':
            try:
                db.create_all()
            except Exception as e:
                logger.warning(f"Error al crear tablas: {e}")

            db_url = app.config.get('SQLALCHEMY_DATABASE_URI', '')
            is_postgresql = 'postgresql' in db_url

            try:
                if is_postgresql:
                    from sqlalchemy import inspect
                    inspector = inspect(db.engine)
                    existing_columns = {col['name'] for col in inspector.get_columns('cursos')}

                    if 'dias_semana' not in existing_columns:
                        db.session.execute(text("ALTER TABLE cursos ADD COLUMN dias_semana VARCHAR(20)"))
                        db.session.commit()
                        logger.info('[OK] Columna añadida: cursos.dias_semana')

                    if 'sesiones_por_semana' not in existing_columns:
                        db.session.execute(text("ALTER TABLE cursos ADD COLUMN sesiones_por_semana INTEGER DEFAULT 0"))
                        db.session.commit()
                        logger.info('[OK] Columna añadida: cursos.sesiones_por_semana')
                else:
                    existing = {row[1] for row in db.session.execute(text("PRAGMA table_info('cursos')")).fetchall()}
                    if 'dias_semana' not in existing:
                        db.session.execute(text("ALTER TABLE cursos ADD COLUMN dias_semana VARCHAR(20)"))
                        logger.info('[OK] Columna añadida: cursos.dias_semana')
                    if 'sesiones_por_semana' not in existing:
                        db.session.execute(text("ALTER TABLE cursos ADD COLUMN sesiones_por_semana INTEGER DEFAULT 0"))
                        logger.info('[OK] Columna añadida: cursos.sesiones_por_semana')
                    db.session.commit()
            except Exception as e:
                db.session.rollback()
                logger.warning(f"[WARN] No se pudo asegurar columnas en 'cursos': {e}")

            try:
                institucion = Institucion.query.filter_by(nombre='Universidad Default').first()
                if not institucion:
                    institucion = Institucion(
                        nombre='Universidad Default',
                        ciudad='Bogotá',
                        pais='Colombia',
                        activo=True
                    )
                    db.session.add(institucion)
                    db.session.commit()
                    logger.info("[OK] Institucion creada: Universidad Default")
                else:
                    logger.info("[INFO] Institucion ya existe")

                if not Usuario.query.filter_by(email='admin@universitario.edu').first():
                    admin_global = Usuario(
                        institucion_id=institucion.id,
                        email='admin@universitario.edu',
                        password=encriptar_contraseña('Admin123!'),
                        nombre='Administrador',
                        apellido='Global',
                        role='admin_global',
                        estado='activo'
                    )
                    db.session.add(admin_global)
                    db.session.commit()
                    logger.info("[OK] Admin global creado")

                if not Usuario.query.filter_by(email='admin.local@universitario.edu').first():
                    admin_local = Usuario(
                        institucion_id=institucion.id,
                        email='admin.local@universitario.edu',
                        password=encriptar_contraseña('Admin123!'),
                        nombre='Administrador',
                        apellido='Local',
                        role='admin_local',
                        estado='activo'
                    )
                    db.session.add(admin_local)
                    db.session.commit()
                    logger.info("[OK] Admin local creado")

            except Exception as e:
                db.session.rollback()
                logger.warning(f"[WARN] Error al crear datos iniciales: {e}")
    
    @app.route('/')
    def index():
        """Redirigir a login"""
        return redirect(url_for('auth.login'))
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5000)