#!/usr/bin/env python
"""Script para ejecutar migraciones SQL"""
import os
import sys
from app import create_app, db
from sqlalchemy import text

def run_migrations():
    """Ejecuta los scripts SQL en el directorio migrations/"""
    config_name = os.getenv('FLASK_ENV', 'production')
    app = create_app(config_name=config_name)
    
    migrations_dir = os.path.join(os.path.dirname(__file__), 'migrations')
    migration_files = [
        'add_authentication_fields.sql',
        'add_contraseña_cambiada.sql',
        'create_solicitudes_nuevo_estudiante.sql',
        'create_actividades.sql',
        'create_calificaciones.sql'
    ]
    
    with app.app_context():
        for migration_file in migration_files:
            migration_path = os.path.join(migrations_dir, migration_file)
            if os.path.exists(migration_path):
                try:
                    with open(migration_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Dividir por ; y ejecutar cada comando por separado
                    commands = content.split(';')
                    
                    for command in commands:
                        # Limpiar comentarios y espacios en blanco
                        lines = []
                        for line in command.split('\n'):
                            # Remover comentarios SQL
                            if '--' in line:
                                line = line[:line.index('--')]
                            line = line.strip()
                            if line:
                                lines.append(line)
                        
                        sql_command = ' '.join(lines)
                        
                        # Ignorar comandos vacíos y COMMIT
                        if sql_command and sql_command.upper() != 'COMMIT':
                            try:
                                db.session.execute(text(sql_command))
                            except Exception as e:
                                # Algunos comandos como ALTER TABLE IF NOT EXISTS pueden fallar si ya existen
                                if 'already exists' in str(e) or 'does not exist' in str(e):
                                    print(f"  ℹ️  {migration_file}: {str(e)}")
                                else:
                                    raise
                    
                    db.session.commit()
                    print(f"✓ Migración aplicada: {migration_file}")
                    
                except Exception as e:
                    print(f"❌ Error en {migration_file}: {str(e)}")
                    db.session.rollback()
                    sys.exit(1)
            else:
                print(f"⚠️  Archivo no encontrado: {migration_file}")

if __name__ == '__main__':
    try:
        run_migrations()
        print("\n✓ Todas las migraciones completadas exitosamente")
    except Exception as e:
        print(f"\n❌ Migraciones fallaron: {str(e)}")
        sys.exit(1)
