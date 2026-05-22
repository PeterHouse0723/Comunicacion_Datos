"""Script para simular actividades y calificaciones en los cursos"""
import sys
from datetime import datetime, timedelta
from pathlib import Path
from random import uniform, randint

# Agregar el directorio padre al path para importar módulos
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app
from extensions import db
from models import (
    Curso, Actividad, Calificacion, EstudianteCurso, Usuario
)

def simular_actividades_curso(curso):
    """Simula 9 actividades para un curso (1 cada 2 semanas)"""
    
    tipos_evaluacion = ['Taller', 'Parcial', 'Proyecto', 'Examen', 'Tarea']
    
    # Obtener fecha de inicio del período
    fecha_inicio = curso.periodo.fecha_inicio if curso.periodo else datetime.now().date()
    
    actividades_creadas = []
    
    for i in range(1, 10):  # 9 actividades
        # Calcular fecha (1 cada 2 semanas)
        semana = i * 2
        fecha_asignacion = fecha_inicio + timedelta(weeks=i*2-2)
        fecha_vencimiento = fecha_asignacion + timedelta(days=7)
        
        # Alternar tipos de evaluación
        tipo = tipos_evaluacion[i % len(tipos_evaluacion)]
        
        # Crear actividad
        actividad = Actividad(
            curso_id=curso.id,
            nombre=f"{tipo} {i} - {curso.nombre}",
            descripcion=f"Evaluación {tipo.lower()} número {i} del curso {curso.nombre}",
            tipo_evaluacion=tipo.lower(),
            semana=semana,
            ponderacion=1.0 / 9,  # Todas tienen igual peso (11.11%)
            fecha_asignacion=fecha_asignacion,
            fecha_vencimiento=fecha_vencimiento,
            activa=True
        )
        
        db.session.add(actividad)
        db.session.flush()  # Para obtener el ID
        
        actividades_creadas.append(actividad)
    
    return actividades_creadas

def simular_calificaciones_actividad(actividad):
    """Simula calificaciones para todos los estudiantes de un curso"""
    
    # Obtener todos los estudiantes del curso
    estudiantes = (
        Usuario.query
        .join(EstudianteCurso)
        .filter(EstudianteCurso.curso_id == actividad.curso_id)
        .all()
    )
    
    for estudiante in estudiantes:
        # Verificar si ya existe calificación
        calif_existente = Calificacion.query.filter_by(
            actividad_id=actividad.id,
            estudiante_id=estudiante.id
        ).first()
        
        if calif_existente:
            continue
        
        # Generar nota simulada (entre 2.5 y 5.0, con tendencia a notas más altas)
        nota_base = uniform(2.5, 5.0)
        # Ajustar distribución: 40% más probabilidad de notas altas
        if uniform(0, 1) < 0.4:
            nota_base = uniform(3.8, 5.0)
        
        nota = round(nota_base, 1)
        
        # Retroalimentación simulada
        retroalimentaciones = [
            "Excelente trabajo. Siga así.",
            "Buen desempeño.",
            "Trabajo aceptable. Puede mejorar en...",
            "Necesita más dedicación en los temas tratados.",
            "Trabajo incompleto. Revise los criterios de evaluación.",
            "Muy buena participación.",
            "Cumple con los requisitos mínimos.",
        ]
        
        retroalimentacion = retroalimentaciones[randint(0, len(retroalimentaciones)-1)]
        
        calificacion = Calificacion(
            actividad_id=actividad.id,
            estudiante_id=estudiante.id,
            valor_nota=nota,
            retroalimentacion=retroalimentacion,
            fecha_calificacion=actividad.fecha_vencimiento + timedelta(days=randint(1, 3))
        )
        
        db.session.add(calificacion)
    
    return len(estudiantes)

def main():
    """Ejecuta la simulación de actividades y calificaciones"""
    
    app = create_app()
    
    with app.app_context():
        print("=" * 60)
        print("INICIANDO SIMULACION DE ACTIVIDADES Y CALIFICACIONES")
        print("=" * 60)
        
        # Obtener todos los cursos activos
        cursos = Curso.query.filter_by(activo=True).all()
        
        if not cursos:
            print("[!] No hay cursos activos para simular.")
            return
        
        print(f"\n[*] Encontrados {len(cursos)} cursos activos\n")
        
        total_actividades = 0
        total_calificaciones = 0
        
        for curso in cursos:
            print(f"[>] Procesando: {curso.nombre}")
            
            # Verificar si ya tienen actividades
            actividades_existentes = Actividad.query.filter_by(curso_id=curso.id).count()
            
            if actividades_existentes > 0:
                print(f"    [!] Ya tiene {actividades_existentes} actividades. Saltando...\n")
                continue
            
            # Crear 9 actividades
            actividades = simular_actividades_curso(curso)
            print(f"    [+] Creadas {len(actividades)} actividades")
            
            # Crear calificaciones para cada actividad
            for actividad in actividades:
                num_califs = simular_calificaciones_actividad(actividad)
                print(f"        - {actividad.nombre}: {num_califs} calificaciones")
                total_calificaciones += num_califs
            
            total_actividades += len(actividades)
            print()
        
        # Confirmar cambios
        db.session.commit()
        
        print("=" * 60)
        print("[+] SIMULACION COMPLETADA")
        print(f"    - Actividades creadas: {total_actividades}")
        print(f"    - Calificaciones asignadas: {total_calificaciones}")
        print("=" * 60)

if __name__ == '__main__':
    main()
