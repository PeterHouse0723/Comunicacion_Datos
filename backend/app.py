from flask import Flask, render_template, redirect, url_for
from extensions import db, migrate
from config import config
import os

# Importar modelos después de db esté disponible
from models import (Usuario, Role, Curso, Nota, Asistencia, 
                    LoginAuditoria, Notificacion, AlertaRiesgoAcademico, CursoDocente)

def create_app(config_name=None):
    """Factory para crear la aplicación Flask"""
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')
    
    app = Flask(__name__, template_folder='templates', static_folder='static')
    app.config.from_object(config[config_name])
    
    # Inicializar BD
    db.init_app(app)
    migrate.init_app(app, db)
    
    # Registrar blueprints (rutas)
    from routes.auth import auth_bp
    app.register_blueprint(auth_bp)
    
    # Crear tablas si no existen
    with app.app_context():
        db.create_all()
        
        # Crear roles por defecto si no existen
        # Solo insertar si la tabla está vacía
        try:
            if db.session.query(Role).count() == 0:
                roles_default = ['admin', 'docente', 'estudiante']
                for rol_nombre in roles_default:
                    rol = Role(
                        nombre=rol_nombre,
                        descripcion=f'Rol de {rol_nombre}'
                    )
                    db.session.add(rol)
                db.session.commit()
                print("✅ Roles creados exitosamente")
        except Exception as e:
            db.session.rollback()
            print(f"⚠️ Roles ya existen o error: {e}")
    
    @app.route('/')
    def index():
        return redirect(url_for('auth.login'))
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5000)