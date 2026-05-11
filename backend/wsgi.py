"""Archivo de entrada WSGI para producción"""
import os
from app import create_app, db
from models import Institucion, Usuario, Periodo, Curso, CursoDocente, EstudianteCurso, SolicitudEstudianteMateria, Clase, Nota, Asistencia, AlertaRiesgoAcademico, LoginAuditoria, Notificacion

# Crear la aplicación con configuración de producción
app = create_app(config_name='production')

# Contexto de aplicación para operaciones CLI
@app.shell_context_processor
def make_shell_context():
    return {
        'db': db,
        'Institucion': Institucion,
        'Usuario': Usuario,
        'Periodo': Periodo,
        'Curso': Curso,
        'CursoDocente': CursoDocente,
        'EstudianteCurso': EstudianteCurso,
        'SolicitudEstudianteMateria': SolicitudEstudianteMateria,
        'Clase': Clase,
        'Nota': Nota,
        'Asistencia': Asistencia,
        'AlertaRiesgoAcademico': AlertaRiesgoAcademico,
        'LoginAuditoria': LoginAuditoria,
        'Notificacion': Notificacion,
    }

if __name__ == '__main__':
    app.run()
