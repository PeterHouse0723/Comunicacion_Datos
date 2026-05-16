-- Creación de tabla MENSAJES para sistema de mensajería entre docentes y estudiantes
-- Fecha: 2026-05-16

CREATE TABLE IF NOT EXISTS mensajes (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    remitente_id INTEGER NOT NULL,
    destinatario_id INTEGER NOT NULL,
    curso_id INTEGER NOT NULL,
    contenido LONGTEXT NOT NULL,
    leido BOOLEAN DEFAULT FALSE,
    fecha_lectura DATETIME,
    fecha_creacion DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    -- Claves foráneas
    CONSTRAINT fk_mensaje_remitente FOREIGN KEY (remitente_id) 
        REFERENCES usuarios(id) ON DELETE CASCADE,
    CONSTRAINT fk_mensaje_destinatario FOREIGN KEY (destinatario_id) 
        REFERENCES usuarios(id) ON DELETE CASCADE,
    CONSTRAINT fk_mensaje_curso FOREIGN KEY (curso_id) 
        REFERENCES cursos(id) ON DELETE CASCADE,
    
    -- Índices para consultas rápidas
    INDEX idx_mensaje_remitente_destinatario (remitente_id, destinatario_id),
    INDEX idx_mensaje_curso (curso_id),
    INDEX idx_mensaje_fecha_creacion (fecha_creacion),
    INDEX idx_mensaje_leido (leido),
    INDEX idx_mensaje_destinatario (destinatario_id)
);
