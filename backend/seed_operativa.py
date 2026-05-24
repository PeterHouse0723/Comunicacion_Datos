"""
Script para cargar las actividades del curso Operativa.

Uso local:
    cd backend
    python seed_operativa.py

Uso en Render Shell:
    cd backend
    python seed_operativa.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
from extensions import db
from models import Curso, Actividad
from datetime import date, timedelta

ACTIVIDADES = [
    {'nombre': 'R1-A1-S3 Ruta Óptima en Dos Variables',                'semana': 3},
    {'nombre': 'R1-A2-S6 Óptimo con Evidencias',                       'semana': 6},
    {'nombre': 'R2-A3-S9 De gráfico a álgebra: simplex en acción',     'semana': 9},
    {'nombre': 'R2-A4-S12 Decidir con dualidad: sensibilidad que convence', 'semana': 12},
    {'nombre': 'R3-A5-S12 Mapa de Urgencias Viales',                   'semana': 12},
    {'nombre': 'R3-A6-S13 Ruta Crítica del Territorio',                'semana': 13},
    {'nombre': 'R3-A7-S15 Redes que Reconectan',                       'semana': 15},
    {'nombre': 'R3-A8-S16 Calendario que Sostiene',                    'semana': 16},
]

INICIO_SEMESTRE = date(2026, 1, 12)

app = create_app()

with app.app_context():
    curso = Curso.query.filter(Curso.nombre.ilike('%operativa%')).first()
    if not curso:
        print("ERROR: No se encontró ningún curso con nombre 'Operativa'.")
        print("Crea el curso primero desde la interfaz gráfica y vuelve a ejecutar este script.")
        sys.exit(1)

    print(f"Curso encontrado: {curso.nombre} (id={curso.id})")

    existentes = Actividad.query.filter_by(curso_id=curso.id).count()
    if existentes > 0:
        print(f"El curso ya tiene {existentes} actividades. No se crearon duplicados.")
        sys.exit(0)

    for act in ACTIVIDADES:
        s = act['semana']
        f_asig = INICIO_SEMESTRE + timedelta(weeks=(s - 1))
        f_venc = f_asig + timedelta(days=7)
        db.session.add(Actividad(
            curso_id=curso.id,
            nombre=act['nombre'],
            tipo_evaluacion='tarea',
            semana=s,
            ponderacion=round(1 / 8, 4),
            fecha_asignacion=f_asig,
            fecha_vencimiento=f_venc,
            activa=True,
        ))
        print(f"  + {act['nombre']}  (semana {s}, asig={f_asig}, venc={f_venc})")

    db.session.commit()
    print(f"\n[OK] {len(ACTIVIDADES)} actividades creadas correctamente para el curso '{curso.nombre}'.")
