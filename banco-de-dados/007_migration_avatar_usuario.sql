-- ============================================================
-- MIGRATION: avatar_url no perfil de usuario
-- ============================================================

ALTER TABLE usuarios
    ADD COLUMN IF NOT EXISTS avatar_url TEXT;
