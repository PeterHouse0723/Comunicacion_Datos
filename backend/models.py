"""Modelos de base de datos"""
from extensions import db
from datetime import datetime
from enum import Enum

class RoleEnum(Enum):
    """Roles disponibles en el sistema"""
    ADMIN = "admin"
    DOCENTE = "docente"
    ESTUDIANTE = "estudiante"

class Role(db.Model):
    """Tabla de roles"""
    __tablename__ = 'roles'
    
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), unique=True, nullable=False)
    descripcion = db.Column(db.String(255))
    
    # Relaciones
    usuarios = db.relationship('Usuario', backref='role', lazy=True)
    
    def __repr__(self):
        return f'<Role {self.nombre}>'

class Usuario(db.Model):
    """Tabla de usuarios (estudiantes, docentes, admin)"""
    __tablename__ = 'usuarios'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password = db.Column(db.String(255), nullable=False)
    nombre = db.Column(db.String(120), nullable=False)
    apellido = db.Column(db.String(120), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    activo = db.Column(db.Boolean, default=True)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_actualizacion = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relaciones
    auditorias_login = db.relationship('LoginAuditoria', backref='usuario', lazy=True)
    notas = db.relationship('Nota', backref='estudiante', lazy=True, foreign_keys='Nota.estudiante_id')
    asistencias = db.relationship('Asistencia', backref='estudiante', lazy=True, foreign_keys='Asistencia.estudiante_id')
    cursos = db.relationship('Curso', secondary='curso_docente', backref='docentes')
    
    def __repr__(self):
        return f'<Usuario {self.email}>'

class Curso(db.Model):
    """Tabla de cursos/materias"""
    __tablename__ = 'cursos'
    
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(120), nullable=False)
    codigo = db.Column(db.String(50), unique=True, nullable=False)
    descripcion = db.Column(db.String(255))
    creditos = db.Column(db.Integer)
    fecha_inicio = db.Column(db.Date)
    fecha_fin = db.Column(db.Date)
    activo = db.Column(db.Boolean, default=True)
    
    # Relaciones
    notas = db.relationship('Nota', backref='curso', lazy=True, cascade='all, delete-orphan')
    asistencias = db.relationship('Asistencia', backref='curso', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Curso {self.nombre}>'

class CursoDocente(db.Model):
    """Tabla de relación entre cursos y docentes (un docente puede dictar varios cursos)"""
    __tablename__ = 'curso_docente'
    
    id = db.Column(db.Integer, primary_key=True)
    curso_id = db.Column(db.Integer, db.ForeignKey('cursos.id'), nullable=False)
    docente_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    
class Nota(db.Model):
    """Tabla de calificaciones de estudiantes"""
    __tablename__ = 'notas'
    
    id = db.Column(db.Integer, primary_key=True)
    estudiante_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False, index=True)
    curso_id = db.Column(db.Integer, db.ForeignKey('cursos.id'), nullable=False, index=True)
    parcial_1 = db.Column(db.Float)
    parcial_2 = db.Column(db.Float)
    parcial_3 = db.Column(db.Float)
    examen_final = db.Column(db.Float)
    promedio_final = db.Column(db.Float)
    estado = db.Column(db.String(50), default='en_curso')  # en_curso, aprobado, reprobado
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)
    
    def calcular_promedio(self):
        """Calcula el promedio final automáticamente"""
        notas = [n for n in [self.parcial_1, self.parcial_2, self.parcial_3, self.examen_final] if n is not None]
        if notas:
            self.promedio_final = sum(notas) / len(notas)
    
    def __repr__(self):
        return f'<Nota Estudiante: {self.estudiante_id}, Curso: {self.curso_id}>'

class Asistencia(db.Model):
    """Tabla de asistencia de estudiantes"""
    __tablename__ = 'asistencias'
    
    id = db.Column(db.Integer, primary_key=True)
    estudiante_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False, index=True)
    curso_id = db.Column(db.Integer, db.ForeignKey('cursos.id'), nullable=False, index=True)
    fecha = db.Column(db.Date, nullable=False)
    presente = db.Column(db.Boolean, default=True)
    justificacion = db.Column(db.String(255))
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Asistencia Estudiante: {self.estudiante_id}, Fecha: {self.fecha}>'

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
        return f'<LoginAuditoria Usuario: {self.usuario_id}, Fecha: {self.fecha_login}>'

class Notificacion(db.Model):
    """Tabla de notificaciones para usuarios"""
    __tablename__ = 'notificaciones'
    
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False, index=True)
    titulo = db.Column(db.String(120), nullable=False)
    mensaje = db.Column(db.Text, nullable=False)
    tipo = db.Column(db.String(50), default='info')  # info, warning, danger, success
    leida = db.Column(db.Boolean, default=False)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_lectura = db.Column(db.DateTime)
    
    def __repr__(self):
        return f'<Notificacion {self.titulo}>'

class AlertaRiesgoAcademico(db.Model):
    """Tabla para alertas de riesgo académico"""
    __tablename__ = 'alertas_riesgo'
    
    id = db.Column(db.Integer, primary_key=True)
    estudiante_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False, index=True)
    curso_id = db.Column(db.Integer, db.ForeignKey('cursos.id'), nullable=False)
    tipo_alerta = db.Column(db.String(100))  # bajo_promedio, faltas_excesivas, en_riesgo
    promedio_actual = db.Column(db.Float)
    porcentaje_asistencia = db.Column(db.Float)
    fecha_alerta = db.Column(db.DateTime, default=datetime.utcnow)
    estado = db.Column(db.String(50), default='activa')  # activa, resuelta
    
    def __repr__(self):
        return f'<AlertaRiesgo Estudiante: {self.estudiante_id}>'
