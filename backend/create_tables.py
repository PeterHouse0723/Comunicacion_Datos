#!/usr/bin/env python
"""
Script para ejecutar migraciones en la base de datos
Uso: python -m backend.create_tables
O desde el directorio del proyecto: python backend/create_tables.py
"""

import sys
import os

# Agregar el directorio backend al path
sys.path.insert(0, os.path.dirname(__file__))

def main():
    """Ejecuta las migraciones"""
    try:
        from app import create_app
        
        print("🔄 Inicializando aplicación...")
        app = create_app('production')
        
        print("✅ Aplicación inicializada")
        print("✅ Las migraciones se han ejecutado automáticamente")
        print("\n📊 Tabla 'mensajes' debería estar creada en la base de datos")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
