-- Migración: Crear tabla de solicitudes de nuevos estudiantes
-- Descripción: Permite que los docentes soliciten la inscripción de estudiantes nuevos

-- Crear tabla solicitudes_nuevo_estudiante
CREATE TABLE IF NOT EXISTS solicitudes_nuevo_estudiante (
    id SERIAL PRIMARY KEY,
    curso_id INTEGER NOT NULL,
    docente_id INTEGER NOT NULL,
    admin_local_id INTEGER,
    nombre VARCHAR(120) NOT NULL,
    apellido VARCHAR(120) NOT NULL,
    correo VARCHAR(120) NOT NULL,
    estado VARCHAR(30) DEFAULT 'pendiente' NOT NULL,
    motivo_rechazo TEXT,
    fecha_solicitud TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_resolucion TIMESTAMP,
    estudiante_id INTEGER,
    FOREIGN KEY (curso_id) REFERENCES cursos (id),
    FOREIGN KEY (docente_id) REFERENCES usuarios (id),
    FOREIGN KEY (admin_local_id) REFERENCES usuarios (id),
    FOREIGN KEY (estudiante_id) REFERENCES usuarios (id)
);

-- Crear índices para mejor rendimiento
CREATE INDEX IF NOT EXISTS idx_solicitudes_nuevo_estudiante_docente_id ON solicitudes_nuevo_estudiante (docente_id);
CREATE INDEX IF NOT EXISTS idx_solicitudes_nuevo_estudiante_admin_local_id ON solicitudes_nuevo_estudiante (admin_local_id);
CREATE INDEX IF NOT EXISTS idx_solicitudes_nuevo_estudiante_curso_id ON solicitudes_nuevo_estudiante (curso_id);
CREATE INDEX IF NOT EXISTS idx_solicitudes_nuevo_estudiante_correo ON solicitudes_nuevo_estudiante (correo);
CREATE INDEX IF NOT EXISTS idx_solicitudes_nuevo_estudiante_estado ON solicitudes_nuevo_estudiante (estado);
CREATE INDEX IF NOT EXISTS idx_solicitudes_nuevo_estudiante_estudiante_id ON solicitudes_nuevo_estudiante (estudiante_id);
