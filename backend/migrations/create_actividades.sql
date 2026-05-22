-- Creación de tabla ACTIVIDADES para almacenar actividades de cursos
-- Fecha: 2026-05-22
-- Base de datos: PostgreSQL

CREATE TABLE IF NOT EXISTS actividades (
    id SERIAL PRIMARY KEY,
    curso_id INTEGER NOT NULL,
    nombre VARCHAR(255) NOT NULL,
    descripcion TEXT,
    tipo_evaluacion VARCHAR(50) NOT NULL,
    semana INTEGER NOT NULL,
    ponderacion DECIMAL(5, 2),
    fecha_asignacion TIMESTAMP,
    fecha_vencimiento TIMESTAMP,
    activa BOOLEAN DEFAULT TRUE,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Claves foráneas
    CONSTRAINT fk_actividad_curso FOREIGN KEY (curso_id) 
        REFERENCES cursos(id) ON DELETE CASCADE
);

-- Crear índices para consultas rápidas
CREATE INDEX IF NOT EXISTS idx_actividad_curso ON actividades (curso_id);
CREATE INDEX IF NOT EXISTS idx_actividad_semana ON actividades (semana);
CREATE INDEX IF NOT EXISTS idx_actividad_activa ON actividades (activa);
CREATE INDEX IF NOT EXISTS idx_actividad_tipo_evaluacion ON actividades (tipo_evaluacion);
