-- Actividades de apoyo académico creadas por docentes para estudiantes específicos
-- Fecha: 2026-05-23

CREATE TABLE IF NOT EXISTS actividades_apoyo (
    id SERIAL PRIMARY KEY,
    curso_id INTEGER NOT NULL,
    docente_id INTEGER NOT NULL,
    titulo VARCHAR(255) NOT NULL,
    descripcion TEXT,
    fecha_vencimiento DATE,
    activa BOOLEAN DEFAULT TRUE,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_apoyo_curso FOREIGN KEY (curso_id) REFERENCES cursos(id) ON DELETE CASCADE,
    CONSTRAINT fk_apoyo_docente FOREIGN KEY (docente_id) REFERENCES usuarios(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_apoyo_curso ON actividades_apoyo (curso_id);
CREATE INDEX IF NOT EXISTS idx_apoyo_docente ON actividades_apoyo (docente_id);

CREATE TABLE IF NOT EXISTS asignaciones_apoyo (
    id SERIAL PRIMARY KEY,
    actividad_apoyo_id INTEGER NOT NULL,
    estudiante_id INTEGER NOT NULL,
    completada BOOLEAN DEFAULT FALSE,
    fecha_completado TIMESTAMP,
    nota_id_reemplazada INTEGER,
    nota_nueva DECIMAL(3,1),
    motivo_reemplazo TEXT,
    CONSTRAINT fk_asig_actividad FOREIGN KEY (actividad_apoyo_id) REFERENCES actividades_apoyo(id) ON DELETE CASCADE,
    CONSTRAINT fk_asig_estudiante FOREIGN KEY (estudiante_id) REFERENCES usuarios(id) ON DELETE CASCADE,
    CONSTRAINT fk_asig_nota FOREIGN KEY (nota_id_reemplazada) REFERENCES notas(id) ON DELETE SET NULL,
    CONSTRAINT uq_apoyo_estudiante UNIQUE (actividad_apoyo_id, estudiante_id)
);

CREATE INDEX IF NOT EXISTS idx_asig_actividad ON asignaciones_apoyo (actividad_apoyo_id);
CREATE INDEX IF NOT EXISTS idx_asig_estudiante ON asignaciones_apoyo (estudiante_id);
