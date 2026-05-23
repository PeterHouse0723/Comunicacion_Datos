-- Agregar soporte para reemplazar Calificacion (ademas de Nota) en asignaciones_apoyo
-- Fecha: 2026-05-23

ALTER TABLE asignaciones_apoyo ADD COLUMN IF NOT EXISTS calificacion_id_reemplazada INTEGER REFERENCES calificaciones(id) ON DELETE SET NULL;
