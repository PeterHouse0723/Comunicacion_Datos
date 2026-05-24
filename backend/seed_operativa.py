"""
Script para cargar actividades y notas del curso Operativa.

Uso local o en Render Shell:
    cd backend
    python seed_operativa.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
from extensions import db
from models import Curso, Actividad, EstudianteCurso, Usuario, Calificacion
from datetime import date, timedelta, datetime
from random import uniform, random

ACTIVIDADES = [
    {'nombre': 'R1-A1-S3 Ruta Optima en Dos Variables',                'semana': 3},
    {'nombre': 'R1-A2-S6 Optimo con Evidencias',                       'semana': 6},
    {'nombre': 'R2-A3-S9 De grafico a algebra: simplex en accion',     'semana': 9},
    {'nombre': 'R2-A4-S12 Decidir con dualidad: sensibilidad que convence', 'semana': 12},
    {'nombre': 'R3-A5-S12 Mapa de Urgencias Viales',                   'semana': 12},
    {'nombre': 'R3-A6-S13 Ruta Critica del Territorio',                'semana': 13},
    {'nombre': 'R3-A7-S15 Redes que Reconectan',                       'semana': 15},
    {'nombre': 'R3-A8-S16 Calendario que Sostiene',                    'semana': 16},
]

INICIO_SEMESTRE = date(2026, 1, 12)


def nota_aleatoria():
    r = random()
    if r < 0.60:
        return round(uniform(3.5, 5.0), 1)
    elif r < 0.85:
        return round(uniform(3.0, 3.5), 1)
    else:
        return round(uniform(1.5, 2.9), 1)


app = create_app()

with app.app_context():
    curso = Curso.query.filter(Curso.nombre.ilike('%operativa%')).first()
    if not curso:
        print("ERROR: No se encontro el curso Operativa.")
        sys.exit(1)

    print(f"Curso: {curso.nombre} (id={curso.id})")

    # --- Actividades ---
    existentes = Actividad.query.filter_by(curso_id=curso.id).count()
    if existentes > 0:
        print(f"El curso ya tiene {existentes} actividades. Saltando creacion de actividades.")
    else:
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
        db.session.commit()
        print(f"[OK] {len(ACTIVIDADES)} actividades creadas.")

    # --- Notas ---
    actividades = Actividad.query.filter_by(curso_id=curso.id, activa=True).all()
    estudiantes = (
        Usuario.query
        .join(EstudianteCurso, EstudianteCurso.estudiante_id == Usuario.id)
        .filter(EstudianteCurso.curso_id == curso.id)
        .all()
    )

    ya_hay = (
        Calificacion.query
        .join(Actividad)
        .filter(Actividad.curso_id == curso.id)
        .count()
    )
    if ya_hay > 0:
        print(f"Ya existen {ya_hay} notas. Saltando creacion de notas.")
    else:
        creadas = 0
        for actividad in actividades:
            f_calif = datetime.combine(actividad.fecha_vencimiento, datetime.min.time())
            for est in estudiantes:
                db.session.add(Calificacion(
                    actividad_id=actividad.id,
                    estudiante_id=est.id,
                    valor_nota=nota_aleatoria(),
                    retroalimentacion=None,
                    fecha_calificacion=f_calif,
                ))
                creadas += 1
        db.session.commit()
        print(f"[OK] {creadas} notas creadas ({len(estudiantes)} estudiantes x {len(actividades)} actividades).")
