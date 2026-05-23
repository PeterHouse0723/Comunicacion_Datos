-- Agrega columna logo_filename a instituciones
ALTER TABLE instituciones ADD COLUMN IF NOT EXISTS logo_filename VARCHAR(255);
