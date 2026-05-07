"""Modelos de base de datos - Sistema Académico Multi-Institución"""
from extensions import db
from datetime import datetime
from enum import Enum

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
