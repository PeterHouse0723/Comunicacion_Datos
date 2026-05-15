from flask import Flask, render_template, redirect, url_for
from extensions import db, migrate
from config import config
from utils import encriptar_contraseña
import os
from sqlalchemy import text

# Importar modelos después de que db esté disponible
from models import (
    Institucion, Usuario, Periodo, Curso, CursoDocente, EstudianteCurso,
    SolicitudEstudianteMateria, SolicitudNuevoEstudiante, Clase, Nota, Asistencia, AlertaRiesgoAcademico,
    LoginAuditoria, Notificacion
)

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
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(admin_bp)
    
    # Inicialización pesada solo fuera de producción para evitar timeouts en Render.
    if config_name != 'production':
        with app.app_context():
            db.create_all()

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
                        print('[OK] Columna añadida: cursos.dias_semana')

                    if 'sesiones_por_semana' not in existing_columns:
                        db.session.execute(text("ALTER TABLE cursos ADD COLUMN sesiones_por_semana INTEGER DEFAULT 0"))
                        db.session.commit()
                        print('[OK] Columna añadida: cursos.sesiones_por_semana')
                else:
                    existing = {row[1] for row in db.session.execute(text("PRAGMA table_info('cursos')")).fetchall()}
                    if 'dias_semana' not in existing:
                        db.session.execute(text("ALTER TABLE cursos ADD COLUMN dias_semana VARCHAR(20)"))
                        print('[OK] Columna añadida: cursos.dias_semana')
                    if 'sesiones_por_semana' not in existing:
                        db.session.execute(text("ALTER TABLE cursos ADD COLUMN sesiones_por_semana INTEGER DEFAULT 0"))
                        print('[OK] Columna añadida: cursos.sesiones_por_semana')
                    db.session.commit()
            except Exception as e:
                db.session.rollback()
                print(f"[WARN] No se pudo asegurar columnas en 'cursos': {e}")

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
                    print("[OK] Institucion creada: Universidad Default")
                else:
                    print("[INFO] Institucion ya existe")

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
                    print("[OK] Admin global creado")

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
                    print("[OK] Admin local creado")

            except Exception as e:
                db.session.rollback()
                print(f"[WARN] Error al crear datos iniciales: {e}")
    
    @app.route('/')
    def index():
        """Redirigir a login"""
        return redirect(url_for('auth.login'))
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5000)