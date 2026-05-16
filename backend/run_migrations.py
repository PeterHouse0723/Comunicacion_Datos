#!/usr/bin/env python
"""Script para ejecutar migraciones SQL"""
import os
import sys
from app import create_app, db

def run_migrations():
    """Ejecuta los scripts SQL en el directorio migrations/"""
    config_name = os.getenv('FLASK_ENV', 'production')
    app = create_app(config_name=config_name)
    
    migrations_dir = os.path.join(os.path.dirname(__file__), 'migrations')
    migration_files = [
        'add_authentication_fields.sql',
        'add_contraseña_cambiada.sql',
        'create_solicitudes_nuevo_estudiante.sql'
    ]
    
    with app.app_context():
        for migration_file in migration_files:
            migration_path = os.path.join(migrations_dir, migration_file)
            if os.path.exists(migration_path):
                try:
                    with open(migration_path, 'r', encoding='utf-8') as f:
                        sql = f.read()
                    # Ejecutar SQL
                    db.session.execute(db.text(sql))
                    db.session.commit()
                    print(f"✓ Migración aplicada: {migration_file}")
                except Exception as e:
                    print(f"⚠️  Error en {migration_file}: {str(e)}")
                    db.session.rollback()
            else:
                print(f"⚠️  Archivo no encontrado: {migration_file}")

if __name__ == '__main__':
    run_migrations()
    print("Migraciones completadas")
