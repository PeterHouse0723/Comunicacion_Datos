#!/usr/bin/env python
"""
Script CLI para cargar estudiantes desde CSV sin pasar por Gunicorn.
Uso: python scripts/cargar_estudiantes_cli.py <ruta_csv> <curso_id> <institucion_id>
"""
import sys
import csv
import os
from pathlib import Path

# Agregar backend al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app, db
from models import Usuario, EstudianteCurso, Curso
from utils import encriptar_contraseña, validar_email

def cargar_estudiantes_desde_csv(csv_path, curso_id, institucion_id):
    """
    Carga estudiantes desde un CSV sin timeouts.
    
    Args:
        csv_path: Ruta al archivo CSV
        curso_id: ID del curso
        institucion_id: ID de la institución
    """
    # Crear app en contexto de producción
    app = create_app(config_name='production')
    
    with app.app_context():
        # Validar que el curso existe
        curso = Curso.query.get(curso_id)
        if not curso:
            print(f"❌ Error: Curso con ID {curso_id} no encontrado")
            return False
        
        if curso.institucion_id != institucion_id:
            print(f"❌ Error: El curso no pertenece a la institución {institucion_id}")
            return False
        
        # Leer CSV
        if not os.path.exists(csv_path):
            print(f"❌ Error: Archivo {csv_path} no encontrado")
            return False
        
        print(f"📂 Leyendo archivo: {csv_path}")
        
        creados = 0
        inscritos = 0
        errores = 0
        
        try:
            with open(csv_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                
                if not reader.fieldnames:
                    print("❌ Error: CSV vacío")
                    return False
                
                # Normalizar nombres de columnas
                fieldnames_lower = [nombre.strip().lower() for nombre in reader.fieldnames]
                requeridos = {'email', 'nombre', 'apellido'}
                
                if not requeridos.issubset(set(fieldnames_lower)):
                    print(f"❌ Error: CSV debe tener columnas: {', '.join(requeridos)}")
                    return False
                
                # Procesar registros
                registros_validos = []
                vistos = set()
                
                for row in reader:
                    email = (row.get('email') or '').strip().lower()
                    nombre = (row.get('nombre') or '').strip()
                    apellido = (row.get('apellido') or '').strip()
                    
                    if not email or not nombre or not apellido:
                        print(f"⚠️  Fila incompleta ignorada")
                        errores += 1
                        continue
                    
                    if email in vistos:
                        print(f"⚠️  Email duplicado en CSV: {email}")
                        continue
                    
                    vistos.add(email)
                    
                    es_valido, _ = validar_email(email)
                    if not es_valido:
                        print(f"❌ Email inválido: {email}")
                        errores += 1
                        continue
                    
                    registros_validos.append({
                        'email': email,
                        'nombre': nombre,
                        'apellido': apellido
                    })
                
                if not registros_validos:
                    print("❌ No hay registros válidos en el CSV")
                    return False
                
                print(f"✅ Encontrados {len(registros_validos)} registros válidos")
                
                # Obtener emails existentes
                emails_csv = [r['email'] for r in registros_validos]
                usuarios_existentes = Usuario.query.filter(
                    Usuario.email.in_(emails_csv),
                    Usuario.institucion_id == institucion_id
                ).all()
                emails_existentes = {u.email for u in usuarios_existentes}
                
                # Crear nuevos usuarios
                registros_crear = [r for r in registros_validos if r['email'] not in emails_existentes]
                
                if registros_crear:
                    print(f"➕ Creando {len(registros_crear)} nuevos usuarios...")
                    nuevos_usuarios = []
                    
                    for registro in registros_crear:
                        nuevo_usuario = Usuario(
                            institucion_id=institucion_id,
                            email=registro['email'],
                            password=encriptar_contraseña('Estudiante123!'),
                            nombre=registro['nombre'],
                            apellido=registro['apellido'],
                            role='estudiante',
                            estado='activo'
                        )
                        nuevos_usuarios.append(nuevo_usuario)
                    
                    db.session.bulk_save_objects(nuevos_usuarios)
                    db.session.flush()
                    creados = len(nuevos_usuarios)
                    print(f"✅ {creados} usuarios creados")
                
                # Obtener IDs de estudiantes
                estudiantes = Usuario.query.with_entities(Usuario.id, Usuario.email).filter(
                    Usuario.email.in_(emails_csv),
                    Usuario.institucion_id == institucion_id
                ).all()
                email_a_id = {email: estudiante_id for estudiante_id, email in estudiantes}
                
                # Obtener inscripciones existentes
                inscripciones_existentes = EstudianteCurso.query.with_entities(
                    EstudianteCurso.estudiante_id
                ).filter(
                    EstudianteCurso.curso_id == curso_id,
                    EstudianteCurso.estudiante_id.in_(list(email_a_id.values()))
                ).all()
                ids_inscritos = {estudiante_id for (estudiante_id,) in inscripciones_existentes}
                
                # Crear nuevas inscripciones
                print(f"➕ Inscribiendo estudiantes en el curso...")
                nuevas_inscripciones = []
                
                for email in emails_csv:
                    estudiante_id = email_a_id.get(email)
                    if estudiante_id and estudiante_id not in ids_inscritos:
                        nueva_inscripcion = EstudianteCurso(
                            estudiante_id=estudiante_id,
                            curso_id=curso_id
                        )
                        nuevas_inscripciones.append(nueva_inscripcion)
                
                if nuevas_inscripciones:
                    db.session.bulk_save_objects(nuevas_inscripciones)
                    inscritos = len(nuevas_inscripciones)
                    print(f"✅ {inscritos} estudiantes inscritos")
                
                # Commit
                db.session.commit()
                
                print("\n" + "="*50)
                print("✅ CARGA COMPLETADA")
                print("="*50)
                print(f"📊 Resumen:")
                print(f"   ✓ Creados: {creados}")
                print(f"   ✓ Inscritos: {inscritos}")
                print(f"   ⚠️  Errores: {errores}")
                print("="*50)
                
                return True
        
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error durante la carga: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    if len(sys.argv) != 4:
        print("Uso: python scripts/cargar_estudiantes_cli.py <ruta_csv> <curso_id> <institucion_id>")
        print("\nEjemplo:")
        print("  python scripts/cargar_estudiantes_cli.py ./Recursos/estudiantes_39.csv 1 1")
        sys.exit(1)
    
    csv_path = sys.argv[1]
    curso_id = int(sys.argv[2])
    institucion_id = int(sys.argv[3])
    
    exito = cargar_estudiantes_desde_csv(csv_path, curso_id, institucion_id)
    sys.exit(0 if exito else 1)
