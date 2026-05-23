"""Modelos de base de datos - Sistema Académico Multi-Institución"""
from extensions import db
from datetime import datetime, date, timedelta
from enum import Enum
from sqlalchemy import func

# ============================================================================
# ENUMS Y CONSTANTES
# ============================================================================

class RoleEnum(Enum):
    """Roles disponibles en el sistema"""
    ADMIN_GLOBAL = "admin_global"
    ADMIN_LOCAL = "admin_local"
    DOCENTE = "docente"
    ESTUDIANTE = "estudiante"

class EstadoUsuarioEnum(Enum):
    """Estados de usuarios"""
    PENDIENTE = "pendiente"  # Docente esperando aprobación
    ACTIVO = "activo"
    INACTIVO = "inactivo"
    SUSPENDIDO = "suspendido"

# ============================================================================
# TABLA: INSTITUCION
# ============================================================================

class Institucion(db.Model):
    """Tabla de instituciones educativas"""
    __tablename__ = 'instituciones'
    
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(200), unique=True, nullable=False, index=True)
    ciudad = db.Column(db.String(100))
    pais = db.Column(db.String(100), default='Colombia')
    logo_filename = db.Column(db.String(255), nullable=True)
    admin_global_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)
    activo = db.Column(db.Boolean, default=True)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relaciones
    usuarios = db.relationship('Usuario', backref='institucion', lazy=True, foreign_keys='Usuario.institucion_id')
    periodos = db.relationship('Periodo', backref='institucion', lazy=True, cascade='all, delete-orphan')
    cursos = db.relationship('Curso', backref='institucion', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Institucion {self.nombre}>'

# ============================================================================
# TABLA: USUARIO (Todos: admin, docente, estudiante)
# ============================================================================

class Usuario(db.Model):
    """Tabla de usuarios (estudiantes, docentes, admins)"""
    __tablename__ = 'usuarios'
    
    id = db.Column(db.Integer, primary_key=True)
    institucion_id = db.Column(db.Integer, db.ForeignKey('instituciones.id'), nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password = db.Column(db.String(255), nullable=False)
    nombre = db.Column(db.String(120), nullable=False)
    apellido = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(50), nullable=False)  # admin_global, admin_local, docente, estudiante
    estado = db.Column(db.String(50), default='activo')  # pendiente, activo, inactivo, suspendido
    contraseña_cambiada = db.Column(db.Boolean, default=True)  # False si es primer login (requiere cambio obligatorio)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_actualizacion = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relaciones
    auditorias_login = db.relationship('LoginAuditoria', backref='usuario', lazy=True, cascade='all, delete-orphan')
    notificaciones = db.relationship('Notificacion', backref='usuario', lazy=True, cascade='all, delete-orphan')
    alertas_riesgo = db.relationship('AlertaRiesgoAcademico', backref='estudiante', lazy=True, 
                                      foreign_keys='AlertaRiesgoAcademico.estudiante_id', cascade='all, delete-orphan')
    notas = db.relationship('Nota', backref='estudiante', lazy=True, 
                           foreign_keys='Nota.estudiante_id', cascade='all, delete-orphan')
    asistencias = db.relationship('Asistencia', backref='estudiante', lazy=True, 
                                 foreign_keys='Asistencia.estudiante_id', cascade='all, delete-orphan')
    cursos_docente = db.relationship('CursoDocente', backref='docente', lazy=True, 
                                     foreign_keys='CursoDocente.docente_id', cascade='all, delete-orphan')
    cursos_inscritos = db.relationship('EstudianteCurso', backref='estudiante', lazy=True, 
                                      foreign_keys='EstudianteCurso.estudiante_id', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Usuario {self.email} ({self.role})>'

# ============================================================================
# TABLA: PERIODO (Semestres/períodos académicos)
# ============================================================================

class Periodo(db.Model):
    """Tabla de períodos académicos (semestres)"""
    __tablename__ = 'periodos'
    
    id = db.Column(db.Integer, primary_key=True)
    institucion_id = db.Column(db.Integer, db.ForeignKey('instituciones.id'), nullable=False, index=True)
    nombre = db.Column(db.String(100), nullable=False)  # "Semestre I 2026", "Semestre II 2026"
    fecha_inicio = db.Column(db.Date, nullable=False)
    fecha_fin = db.Column(db.Date, nullable=False)
    activo = db.Column(db.Boolean, default=True)
    
    # Relaciones
    cursos = db.relationship('Curso', backref='periodo', lazy=True, cascade='all, delete-orphan')
    clases = db.relationship('Clase', backref='periodo', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Periodo {self.nombre}>'

# ============================================================================
# TABLA: CURSO (Materias/asignaturas)
# ============================================================================

class Curso(db.Model):
    """Tabla de cursos/materias"""
    __tablename__ = 'cursos'
    
    id = db.Column(db.Integer, primary_key=True)
    institucion_id = db.Column(db.Integer, db.ForeignKey('instituciones.id'), nullable=False, index=True)
    periodo_id = db.Column(db.Integer, db.ForeignKey('periodos.id'), nullable=False, index=True)
    nombre = db.Column(db.String(150), nullable=False)
    codigo = db.Column(db.String(50), nullable=False)
    descripcion = db.Column(db.Text)
    creditos = db.Column(db.Integer, default=3)
    docente_principal_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)
    activo = db.Column(db.Boolean, default=True)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    # Días de la semana en que se dicta la materia (enteros 0=Lunes .. 6=Domingo), ej: "0,2,4"
    dias_semana = db.Column(db.String(20))
    # Número de sesiones por semana (opcional, puede derivarse de `dias_semana`)
    sesiones_por_semana = db.Column(db.Integer, default=0)
    
    # Relaciones
    docente_principal = db.relationship('Usuario', foreign_keys=[docente_principal_id])
    docentes = db.relationship('CursoDocente', backref='curso', lazy=True, cascade='all, delete-orphan')
    estudiantes = db.relationship('EstudianteCurso', backref='curso', lazy=True, cascade='all, delete-orphan')
    clases = db.relationship('Clase', backref='curso', lazy=True, cascade='all, delete-orphan')
    notas = db.relationship('Nota', backref='curso', lazy=True, cascade='all, delete-orphan')
    asistencias = db.relationship('Asistencia', backref='curso', lazy=True, cascade='all, delete-orphan')
    alertas_riesgo = db.relationship('AlertaRiesgoAcademico', backref='curso', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Curso {self.codigo} - {self.nombre}>'

    def get_dias_semana_list(self):
        """Devuelve la lista de enteros que representan los días de la semana.

        Formato almacenado: cadena separada por comas con valores 0..6
        """
        if not self.dias_semana:
            return []
        try:
            return [int(x) for x in self.dias_semana.split(',') if x.strip() != '']
        except ValueError:
            return []

    def estimar_total_clases(self):
        """Estima el número total de clases en el periodo según `dias_semana` y fechas del `Periodo`.

        Recorre las fechas entre `periodo.fecha_inicio` y `periodo.fecha_fin` y cuenta los días
        cuyo `weekday()` está en la lista `dias_semana`.
        """
        if not self.periodo:
            return 0
        dias = self.get_dias_semana_list()
        if not dias:
            return 0
        start = self.periodo.fecha_inicio
        end = self.periodo.fecha_fin
        delta = timedelta(days=1)
        cur = start
        count = 0
        while cur <= end:
            if cur.weekday() in dias:
                count += 1
            cur = cur + delta
        return count

    def generar_clases(self, crear_si_no_existen=True):
        """Genera registros `Clase` para cada fecha prevista en el periodo.

        Si `crear_si_no_existen` es True no duplicará clases ya existentes.
        Devuelve la cantidad de clases creadas.
        """
        dias = self.get_dias_semana_list()
        if not dias or not self.periodo:
            return 0
        start = self.periodo.fecha_inicio
        end = self.periodo.fecha_fin
        delta = timedelta(days=1)
        cur = start
        creadas = 0
        while cur <= end:
            if cur.weekday() in dias:
                exists = Clase.query.filter_by(curso_id=self.id, fecha=cur).first()
                if exists and crear_si_no_existen:
                    cur = cur + delta
                    continue
                nueva = Clase(curso_id=self.id, periodo_id=self.periodo_id, fecha=cur)
                db.session.add(nueva)
                creadas += 1
            cur = cur + delta
        db.session.commit()
        return creadas

    def total_clases_programadas(self):
        """Cantidad total de clases planificadas para el semestre según días de clase."""
        return self.estimar_total_clases()

    def resumen_asistencia_estudiante(self, estudiante_id):
        """Calcula un resumen de asistencia del estudiante sobre las clases programadas del curso.

        Devuelve un diccionario con:
        - total_clases_programadas
        - clases_registradas
        - presentes
        - ausentes
        - justificadas
        - porcentaje_asistencia
        - porcentaje_inasistencia
        - porcentaje_registro
        """
        total_programadas = self.total_clases_programadas()

        asistencias = Asistencia.query.filter_by(
            estudiante_id=estudiante_id,
            curso_id=self.id
        ).all()

        presentes = 0
        ausentes = 0
        justificadas = 0
        clases_registradas = 0

        for asistencia in asistencias:
            clases_registradas += 1
            if asistencia.presente:
                presentes += 1
            elif asistencia.justificacion:
                justificadas += 1
            else:
                ausentes += 1

        porcentaje_asistencia = round((presentes / total_programadas) * 100, 2) if total_programadas else 0.0
        porcentaje_inasistencia = round(((ausentes + justificadas) / total_programadas) * 100, 2) if total_programadas else 0.0
        porcentaje_registro = round((clases_registradas / total_programadas) * 100, 2) if total_programadas else 0.0

        return {
            'total_clases_programadas': total_programadas,
            'clases_registradas': clases_registradas,
            'presentes': presentes,
            'ausentes': ausentes,
            'justificadas': justificadas,
            'porcentaje_asistencia': porcentaje_asistencia,
            'porcentaje_inasistencia': porcentaje_inasistencia,
            'porcentaje_registro': porcentaje_registro,
        }

    def sincronizar_alerta_inasistencia(self, estudiante_id, usuario_responsable_id=None, umbral=30.0):
        """Crea o actualiza una alerta de riesgo por inasistencia según el porcentaje calculado."""
        resumen = self.resumen_asistencia_estudiante(estudiante_id)
        porcentaje = resumen['porcentaje_inasistencia']
        alerta = AlertaRiesgoAcademico.query.filter_by(
            estudiante_id=estudiante_id,
            curso_id=self.id,
            tipo_alerta='inasistencia',
            estado='activa'
        ).first()

        if porcentaje >= umbral:
            if not alerta:
                alerta = AlertaRiesgoAcademico(
                    estudiante_id=estudiante_id,
                    curso_id=self.id,
                    tipo_alerta='inasistencia',
                    porcentaje_inasistencia=porcentaje,
                    descripcion=f'Inasistencia del {porcentaje}% sobre el total de clases programadas.',
                    estado='activa'
                )
                db.session.add(alerta)
            else:
                alerta.porcentaje_inasistencia = porcentaje
                alerta.descripcion = f'Inasistencia del {porcentaje}% sobre el total de clases programadas.'
                alerta.estado = 'activa'
            alerta.promedio_actual = None
            alerta.total_notas_bajas = alerta.total_notas_bajas or 0
            if usuario_responsable_id:
                alerta.descripcion = f'Inasistencia del {porcentaje}% sobre el total de clases programadas. Responsable: {usuario_responsable_id}'
        else:
            if alerta:
                alerta.porcentaje_inasistencia = porcentaje
                alerta.descripcion = f'Inasistencia actual del {porcentaje}%, por debajo del umbral.'
                alerta.estado = 'resuelta'
        return resumen

# ============================================================================
# TABLA: CURSO_DOCENTE (Relación M2M: Docentes-Cursos)
# ============================================================================

class CursoDocente(db.Model):
    """Tabla de relación: un docente puede dictar varios cursos"""
    __tablename__ = 'curso_docente'
    
    id = db.Column(db.Integer, primary_key=True)
    curso_id = db.Column(db.Integer, db.ForeignKey('cursos.id'), nullable=False, index=True)
    docente_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False, index=True)
    fecha_asignacion = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Índice único para evitar duplicados
    __table_args__ = (db.UniqueConstraint('curso_id', 'docente_id', name='uq_curso_docente'),)
    
    def __repr__(self):
        return f'<CursoDocente Curso:{self.curso_id}, Docente:{self.docente_id}>'

# ============================================================================
# TABLA: ESTUDIANTE_CURSO (Relación M2M: Estudiantes-Cursos)
# ============================================================================

class EstudianteCurso(db.Model):
    """Tabla de relación: un estudiante puede estar en varios cursos"""
    __tablename__ = 'estudiante_curso'
    
    id = db.Column(db.Integer, primary_key=True)
    estudiante_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False, index=True)
    curso_id = db.Column(db.Integer, db.ForeignKey('cursos.id'), nullable=False, index=True)
    fecha_inscripcion = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Índice único para evitar duplicados
    __table_args__ = (db.UniqueConstraint('estudiante_id', 'curso_id', name='uq_estudiante_curso'),)
    
    def __repr__(self):
        return f'<EstudianteCurso Est:{self.estudiante_id}, Curso:{self.curso_id}>'

# ============================================================================
# TABLA: SOLICITUD_ESTUDIANTE_MATERIA (Solicitud docente para agregar estudiante)
# ============================================================================

class SolicitudEstudianteMateria(db.Model):
    """Solicitudes para agregar estudiantes a una materia"""
    __tablename__ = 'solicitudes_estudiante_materia'

    id = db.Column(db.Integer, primary_key=True)
    curso_id = db.Column(db.Integer, db.ForeignKey('cursos.id'), nullable=False, index=True)
    estudiante_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False, index=True)
    docente_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False, index=True)
    admin_local_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True, index=True)
    estado = db.Column(db.String(30), default='pendiente')  # pendiente, aprobado, rechazado
    motivo = db.Column(db.Text)
    respuesta = db.Column(db.Text)
    fecha_solicitud = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_resolucion = db.Column(db.DateTime)

    curso = db.relationship('Curso', backref='solicitudes_estudiantes', lazy=True)
    estudiante = db.relationship('Usuario', foreign_keys=[estudiante_id])
    docente = db.relationship('Usuario', foreign_keys=[docente_id])
    admin_local = db.relationship('Usuario', foreign_keys=[admin_local_id])

    def __repr__(self):
        return f'<SolicitudEstudianteMateria Curso:{self.curso_id}, Est:{self.estudiante_id}, Estado:{self.estado}>'

# ============================================================================
# TABLA: SOLICITUD_NUEVO_ESTUDIANTE (Solicitud docente para agregar estudiante nuevo)
# ============================================================================

class SolicitudNuevoEstudiante(db.Model):
    """Solicitudes para agregar estudiantes nuevos a través de docentes"""
    __tablename__ = 'solicitudes_nuevo_estudiante'

    id = db.Column(db.Integer, primary_key=True)
    curso_id = db.Column(db.Integer, db.ForeignKey('cursos.id'), nullable=False, index=True)
    docente_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False, index=True)
    admin_local_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True, index=True)
    
    # Datos del estudiante a crear
    nombre = db.Column(db.String(120), nullable=False)
    apellido = db.Column(db.String(120), nullable=False)
    correo = db.Column(db.String(120), nullable=False, index=True)
    
    # Control
    estado = db.Column(db.String(30), default='pendiente')  # pendiente, aprobado, rechazado
    motivo_rechazo = db.Column(db.Text)
    fecha_solicitud = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_resolucion = db.Column(db.DateTime)
    estudiante_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True, index=True)  # Se llena cuando se aprueba
    
    # Relaciones
    curso = db.relationship('Curso', backref='solicitudes_nuevos_estudiantes', lazy=True)
    docente = db.relationship('Usuario', foreign_keys=[docente_id], backref='solicitudes_nuevos_estudiantes')
    admin_local = db.relationship('Usuario', foreign_keys=[admin_local_id], backref='solicitudes_nuevos_estudiantes_resueltas')
    estudiante = db.relationship('Usuario', foreign_keys=[estudiante_id], backref='creado_por_solicitud')
    
    def __repr__(self):
        return f'<SolicitudNuevoEstudiante {self.correo} Curso:{self.curso_id} Estado:{self.estado}>'

# ============================================================================
# TABLA: CLASE (Clases dictadas en un curso)
# ============================================================================

class Clase(db.Model):
    """Tabla de clases (para registro de asistencia por clase)"""
    __tablename__ = 'clases'
    
    id = db.Column(db.Integer, primary_key=True)
    curso_id = db.Column(db.Integer, db.ForeignKey('cursos.id'), nullable=False, index=True)
    periodo_id = db.Column(db.Integer, db.ForeignKey('periodos.id'), nullable=False)
    fecha = db.Column(db.Date, nullable=False)
    numero_clase = db.Column(db.Integer)  # Número secuencial dentro del curso
    tema = db.Column(db.String(200))
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relaciones
    asistencias = db.relationship('Asistencia', backref='clase', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Clase {self.curso_id} - {self.fecha}>'

# ============================================================================
# TABLA: NOTA (Calificaciones - cada entrega es un registro)
# ============================================================================

class Nota(db.Model):
    """Tabla de calificaciones (cada entrega/evaluación es un registro independiente)
    
    Todas las entregas tienen el MISMO peso porcentual.
    Escala: 0.0 - 5.0 (aprueba con 3.2)
    """
    __tablename__ = 'notas'
    
    id = db.Column(db.Integer, primary_key=True)
    estudiante_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False, index=True)
    curso_id = db.Column(db.Integer, db.ForeignKey('cursos.id'), nullable=False, index=True)
    valor_nota = db.Column(db.Float, nullable=False)  # 0.0 a 5.0
    numero_entrega = db.Column(db.Integer)  # 1, 2, 3, ... (secuencial)
    tipo_evaluacion = db.Column(db.String(100))  # "parcial", "taller", "proyecto", "examen"
    descripcion = db.Column(db.String(200))
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Nota Est:{self.estudiante_id}, Curso:{self.curso_id}, Nota:{self.valor_nota}>'
    
    def esta_aprobada(self):
        """Verifica si la nota está aprobada (>= 3.2)"""
        return self.valor_nota >= 3.2

# ============================================================================
# TABLA: ACTIVIDAD (Actividades/Evaluaciones de un curso)
# ============================================================================

class Actividad(db.Model):
    """Tabla de actividades y evaluaciones de un curso"""
    __tablename__ = 'actividades'
    
    id = db.Column(db.Integer, primary_key=True)
    curso_id = db.Column(db.Integer, db.ForeignKey('cursos.id'), nullable=False, index=True)
    nombre = db.Column(db.String(200), nullable=False)
    descripcion = db.Column(db.Text)
    tipo_evaluacion = db.Column(db.String(50), nullable=False)  # taller, parcial, proyecto, examen, tarea
    semana = db.Column(db.Integer)  # Número de semana (1-18)
    ponderacion = db.Column(db.Float, default=1.0)  # Peso porcentual (ej: 0.15 = 15%)
    fecha_asignacion = db.Column(db.Date, nullable=False)
    fecha_vencimiento = db.Column(db.Date, nullable=False)
    activa = db.Column(db.Boolean, default=True)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relaciones
    curso = db.relationship('Curso', backref='actividades', foreign_keys=[curso_id])
    calificaciones = db.relationship('Calificacion', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Actividad {self.nombre}, Semana {self.semana}>'
    
    def promedio_clase(self):
        """Calcula el promedio de la actividad en la clase"""
        if not self.calificaciones:
            return 0.0
        total = sum(c.valor_nota for c in self.calificaciones)
        return round(total / len(self.calificaciones), 2)

# ============================================================================
# TABLA: CALIFICACION (Notas de estudiantes en actividades)
# ============================================================================

class Calificacion(db.Model):
    """Tabla de calificaciones de estudiantes en actividades específicas"""
    __tablename__ = 'calificaciones'
    
    id = db.Column(db.Integer, primary_key=True)
    actividad_id = db.Column(db.Integer, db.ForeignKey('actividades.id'), nullable=False, index=True)
    estudiante_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False, index=True)
    valor_nota = db.Column(db.Float, nullable=False)  # 0.0 a 5.0
    retroalimentacion = db.Column(db.Text)
    fecha_calificacion = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_actualizacion = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relaciones
    actividad = db.relationship('Actividad', foreign_keys=[actividad_id], overlaps="calificaciones")
    estudiante = db.relationship('Usuario', backref='calificaciones', foreign_keys=[estudiante_id])
    
    # Índice único
    __table_args__ = (db.UniqueConstraint('actividad_id', 'estudiante_id', name='uq_actividad_estudiante'),)
    
    def __repr__(self):
        return f'<Calificacion Est:{self.estudiante_id}, Act:{self.actividad_id}, Nota:{self.valor_nota}>'
    
    def esta_aprobada(self):
        """Verifica si la nota está aprobada (>= 3.2)"""
        return self.valor_nota >= 3.2

# ============================================================================
# TABLA: ASISTENCIA (Registro de asistencia por clase)
# ============================================================================

class Asistencia(db.Model):
    """Tabla de asistencia de estudiantes (por clase)"""
    __tablename__ = 'asistencias'
    
    id = db.Column(db.Integer, primary_key=True)
    estudiante_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False, index=True)
    clase_id = db.Column(db.Integer, db.ForeignKey('clases.id'), nullable=False)
    curso_id = db.Column(db.Integer, db.ForeignKey('cursos.id'), nullable=False, index=True)
    presente = db.Column(db.Boolean, default=True)
    justificacion = db.Column(db.String(255))
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Índice único para evitar duplicados (un estudiante no puede tener 2 asistencias en la misma clase)
    __table_args__ = (db.UniqueConstraint('estudiante_id', 'clase_id', name='uq_estudiante_clase'),)
    
    def __repr__(self):
        return f'<Asistencia Est:{self.estudiante_id}, Clase:{self.clase_id}>'

# ============================================================================
# TABLA: ALERTA_RIESGO_ACADEMICO (Sistema de alertas de riesgo)
# ============================================================================

class AlertaRiesgoAcademico(db.Model):
    """Tabla para alertas de riesgo académico
    
    Se activa cuando:
    1. Inasistencia > 35% de clases
    2. Promedio < 3.2
    3. Más de 5 notas por debajo de 3.2
    """
    __tablename__ = 'alertas_riesgo'
    
    id = db.Column(db.Integer, primary_key=True)
    estudiante_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False, index=True)
    curso_id = db.Column(db.Integer, db.ForeignKey('cursos.id'), nullable=False, index=True)
    tipo_alerta = db.Column(db.String(100))  # "inasistencia", "bajo_promedio", "multiples_bajas"
    promedio_actual = db.Column(db.Float)  # Promedio al momento de la alerta
    porcentaje_inasistencia = db.Column(db.Float)  # Porcentaje de inasistencia
    total_notas_bajas = db.Column(db.Integer, default=0)  # Cantidad de notas < 3.2
    fecha_alerta = db.Column(db.DateTime, default=datetime.utcnow)
    estado = db.Column(db.String(50), default='activa')  # activa, resuelta
    descripcion = db.Column(db.Text)
    
    def __repr__(self):
        return f'<AlertaRiesgo Est:{self.estudiante_id}, {self.tipo_alerta}>'

# ============================================================================
# TABLA: LOGIN_AUDITORIA (Auditoría de accesos)
# ============================================================================

class LoginAuditoria(db.Model):
    """Tabla de auditoría: registro de todos los inicios de sesión"""
    __tablename__ = 'login_auditoria'
    
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False, index=True)
    fecha_login = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(45))  # Soporta IPv4 e IPv6
    navegador = db.Column(db.String(255))
    estado = db.Column(db.String(50), default='exitoso')  # exitoso, fallido
    razon_fallo = db.Column(db.String(255))  # Si es fallido
    
    def __repr__(self):
        return f'<LoginAuditoria Usuario:{self.usuario_id}, {self.fecha_login}>'

# ============================================================================
# TABLA: NOTIFICACION (Sistema de notificaciones)
# ============================================================================

class Notificacion(db.Model):
    """Tabla de notificaciones para usuarios"""
    __tablename__ = 'notificaciones'
    
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False, index=True)
    titulo = db.Column(db.String(150), nullable=False)
    mensaje = db.Column(db.Text, nullable=False)
    tipo = db.Column(db.String(50), default='info')  # info, warning, danger, success
    leida = db.Column(db.Boolean, default=False)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_lectura = db.Column(db.DateTime)
    
    def __repr__(self):
        return f'<Notificacion {self.titulo}>'

# ============================================================================
# TABLA: MENSAJE (Sistema de mensajería entre docentes y estudiantes)
# ============================================================================

class Mensaje(db.Model):
    """Tabla de mensajes entre docentes y estudiantes"""
    __tablename__ = 'mensajes'
    
    id = db.Column(db.Integer, primary_key=True)
    remitente_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False, index=True)
    destinatario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False, index=True)
    curso_id = db.Column(db.Integer, db.ForeignKey('cursos.id'), nullable=False, index=True)
    contenido = db.Column(db.Text, nullable=False)
    leido = db.Column(db.Boolean, default=False)
    fecha_lectura = db.Column(db.DateTime)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    # Relaciones
    remitente = db.relationship('Usuario', foreign_keys=[remitente_id], backref='mensajes_enviados')
    destinatario = db.relationship('Usuario', foreign_keys=[destinatario_id], backref='mensajes_recibidos')
    curso = db.relationship('Curso', backref='mensajes')
    
    # Índice compuesto para consultas rápidas de conversaciones
    __table_args__ = (
        db.Index('idx_mensaje_remitente_destinatario', 'remitente_id', 'destinatario_id'),
        db.Index('idx_mensaje_curso', 'curso_id'),
    )
    
    def __repr__(self):
        return f'<Mensaje De:{self.remitente_id}, Para:{self.destinatario_id}, Curso:{self.curso_id}>'
    
    def marcar_como_leido(self):
        """Marca el mensaje como leído"""
        self.leido = True
        self.fecha_lectura = datetime.utcnow()
        return self

# ============================================================================
# TABLA: ACTIVIDAD_APOYO (Actividades de apoyo académico creadas por docentes)
# ============================================================================

class ActividadApoyo(db.Model):
    """Actividades de refuerzo opcionales que el docente asigna a estudiantes específicos."""
    __tablename__ = 'actividades_apoyo'

    id = db.Column(db.Integer, primary_key=True)
    curso_id = db.Column(db.Integer, db.ForeignKey('cursos.id'), nullable=False, index=True)
    docente_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False, index=True)
    titulo = db.Column(db.String(255), nullable=False)
    descripcion = db.Column(db.Text)
    fecha_vencimiento = db.Column(db.Date)
    activa = db.Column(db.Boolean, default=True)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)

    curso = db.relationship('Curso', backref='actividades_apoyo')
    docente = db.relationship('Usuario', foreign_keys=[docente_id])
    asignaciones = db.relationship('AsignacionApoyo', backref='actividad_apoyo', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<ActividadApoyo {self.titulo}>'

# ============================================================================
# TABLA: ASIGNACION_APOYO (Relación estudiante ↔ actividad de apoyo)
# ============================================================================

class AsignacionApoyo(db.Model):
    """Asignación de una actividad de apoyo a un estudiante específico.

    Cuando el estudiante la resuelve satisfactoriamente, el docente puede
    reemplazar una de sus notas bajas indicando el motivo.
    """
    __tablename__ = 'asignaciones_apoyo'

    id = db.Column(db.Integer, primary_key=True)
    actividad_apoyo_id = db.Column(db.Integer, db.ForeignKey('actividades_apoyo.id'), nullable=False, index=True)
    estudiante_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False, index=True)
    completada = db.Column(db.Boolean, default=False)
    fecha_completado = db.Column(db.DateTime, nullable=True)
    # Reemplazo de nota (opcional, lo hace el docente si el estudiante respondió bien)
    nota_id_reemplazada = db.Column(db.Integer, db.ForeignKey('notas.id'), nullable=True)
    nota_nueva = db.Column(db.Float, nullable=True)
    motivo_reemplazo = db.Column(db.Text, nullable=True)

    estudiante = db.relationship('Usuario', foreign_keys=[estudiante_id])
    nota_reemplazada = db.relationship('Nota', foreign_keys=[nota_id_reemplazada])

    __table_args__ = (db.UniqueConstraint('actividad_apoyo_id', 'estudiante_id', name='uq_apoyo_estudiante'),)

    def __repr__(self):
        return f'<AsignacionApoyo Act:{self.actividad_apoyo_id}, Est:{self.estudiante_id}>'
