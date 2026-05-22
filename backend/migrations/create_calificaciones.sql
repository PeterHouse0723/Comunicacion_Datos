-- Creación de tabla CALIFICACIONES para almacenar notas de estudiantes en actividades
-- Fecha: 2026-05-22
-- Base de datos: PostgreSQL

CREATE TABLE IF NOT EXISTS calificaciones (
    id SERIAL PRIMARY KEY,
    actividad_id INTEGER NOT NULL,
    estudiante_id INTEGER NOT NULL,
    valor_nota DECIMAL(3, 1) NOT NULL,
    retroalimentacion TEXT,
    fecha_calificacion TIMESTAMP,
    fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Claves foráneas
    CONSTRAINT fk_calificacion_actividad FOREIGN KEY (actividad_id) 
        REFERENCES actividades(id) ON DELETE CASCADE,
    CONSTRAINT fk_calificacion_estudiante FOREIGN KEY (estudiante_id) 
        REFERENCES usuarios(id) ON DELETE CASCADE,
    
    -- Restricción única para evitar duplicados
    CONSTRAINT uq_calificacion_actividad_estudiante UNIQUE (actividad_id, estudiante_id)
);

-- Crear índices para consultas rápidas
CREATE INDEX IF NOT EXISTS idx_calificacion_actividad ON calificaciones (actividad_id);
CREATE INDEX IF NOT EXISTS idx_calificacion_estudiante ON calificaciones (estudiante_id);
CREATE INDEX IF NOT EXISTS idx_calificacion_fecha_actualizacion ON calificaciones (fecha_actualizacion);
