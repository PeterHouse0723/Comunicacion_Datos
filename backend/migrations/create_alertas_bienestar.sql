CREATE TABLE IF NOT EXISTS alertas_bienestar (
    id SERIAL PRIMARY KEY,
    estudiante_id INTEGER NOT NULL REFERENCES usuarios(id),
    curso_id INTEGER NOT NULL REFERENCES cursos(id),
    tipo VARCHAR(50) NOT NULL,
    nivel_urgencia VARCHAR(20) NOT NULL,
    resumen TEXT NOT NULL,
    revisada BOOLEAN DEFAULT FALSE,
    fecha TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_alertas_bienestar_estudiante_id ON alertas_bienestar(estudiante_id);
CREATE INDEX IF NOT EXISTS ix_alertas_bienestar_curso_id ON alertas_bienestar(curso_id);
CREATE INDEX IF NOT EXISTS ix_alertas_bienestar_fecha ON alertas_bienestar(fecha);
