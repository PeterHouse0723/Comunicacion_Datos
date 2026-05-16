-- Creación de tabla MENSAJES para sistema de mensajería entre docentes y estudiantes
-- Fecha: 2026-05-16
-- Base de datos: PostgreSQL

CREATE TABLE IF NOT EXISTS mensajes (
    id SERIAL PRIMARY KEY,
    remitente_id INTEGER NOT NULL,
    destinatario_id INTEGER NOT NULL,
    curso_id INTEGER NOT NULL,
    contenido TEXT NOT NULL,
    leido BOOLEAN DEFAULT FALSE,
    fecha_lectura TIMESTAMP,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Claves foráneas
    CONSTRAINT fk_mensaje_remitente FOREIGN KEY (remitente_id) 
        REFERENCES usuarios(id) ON DELETE CASCADE,
    CONSTRAINT fk_mensaje_destinatario FOREIGN KEY (destinatario_id) 
        REFERENCES usuarios(id) ON DELETE CASCADE,
    CONSTRAINT fk_mensaje_curso FOREIGN KEY (curso_id) 
        REFERENCES cursos(id) ON DELETE CASCADE
);

-- Crear índices para consultas rápidas
CREATE INDEX IF NOT EXISTS idx_mensaje_remitente_destinatario ON mensajes (remitente_id, destinatario_id);
CREATE INDEX IF NOT EXISTS idx_mensaje_curso ON mensajes (curso_id);
CREATE INDEX IF NOT EXISTS idx_mensaje_fecha_creacion ON mensajes (fecha_creacion);
CREATE INDEX IF NOT EXISTS idx_mensaje_leido ON mensajes (leido);
CREATE INDEX IF NOT EXISTS idx_mensaje_destinatario ON mensajes (destinatario_id);
