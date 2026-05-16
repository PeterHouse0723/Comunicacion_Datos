-- Script de migración para agregar campos de autenticación mejorada
-- Ejecutar este script para actualizar la tabla usuarios

-- Agregar columnas nuevas a la tabla usuarios (si no existen)
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS fecha_actualizacion TIMESTAMP DEFAULT NOW();
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS primer_login BOOLEAN DEFAULT TRUE;
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS contraseña_temporal BOOLEAN DEFAULT FALSE;
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS token_reset VARCHAR(255) NULL DEFAULT NULL;
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS expiracion_token TIMESTAMP NULL DEFAULT NULL;

-- Crear índices para búsquedas rápidas
CREATE INDEX IF NOT EXISTS idx_token_reset ON usuarios(token_reset);
CREATE INDEX IF NOT EXISTS idx_expiracion_token ON usuarios(expiracion_token);
