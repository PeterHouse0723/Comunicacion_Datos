-- Agregar hora de cierre a actividades_apoyo
-- Fecha: 2026-05-23

ALTER TABLE actividades_apoyo ADD COLUMN hora_cierre TIME;
