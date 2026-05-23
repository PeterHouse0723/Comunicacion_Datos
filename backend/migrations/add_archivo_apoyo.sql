-- Agregar campos de archivo a asignaciones_apoyo
-- Fecha: 2026-05-23

ALTER TABLE asignaciones_apoyo ADD COLUMN archivo_nombre VARCHAR(255);
ALTER TABLE asignaciones_apoyo ADD COLUMN archivo_data BYTEA;
ALTER TABLE asignaciones_apoyo ADD COLUMN archivo_tipo VARCHAR(100);
ALTER TABLE asignaciones_apoyo ADD COLUMN fecha_entrega TIMESTAMP;
