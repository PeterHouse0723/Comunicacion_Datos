-- Script de migración para agregar el campo contraseña_cambiada
-- Este campo indica si el usuario ha cambiado su contraseña (True) o aún usa la temporal (False)

ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS "contraseña_cambiada" BOOLEAN DEFAULT TRUE;
CREATE INDEX IF NOT EXISTS idx_contraseña_cambiada ON usuarios(contraseña_cambiada);
