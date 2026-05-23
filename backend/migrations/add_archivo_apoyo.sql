-- Agregar campos de archivo a asignaciones_apoyo
-- Fecha: 2026-05-23

ALTER TABLE asignaciones_apoyo ADD COLUMN IF NOT EXISTS archivo_nombre VARCHAR(255);
ALTER TABLE asignaciones_apoyo ADD COLUMN IF NOT EXISTS archivo_data BYTEA;
ALTER TABLE asignaciones_apoyo ADD COLUMN IF NOT EXISTS archivo_tipo VARCHAR(100);
ALTER TABLE asignaciones_apoyo ADD COLUMN IF NOT EXISTS fecha_entrega TIMESTAMP;
