-- ============================================================
-- MIGRATION: role master (SaaS multiempresa)
-- Execute este arquivo no SQL Editor do Supabase.
-- ============================================================

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'usuarios_tipo_usuario_check'
    ) THEN
        ALTER TABLE usuarios DROP CONSTRAINT usuarios_tipo_usuario_check;
    END IF;
EXCEPTION WHEN undefined_object THEN
    NULL;
END $$;

ALTER TABLE usuarios
    ADD CONSTRAINT usuarios_tipo_usuario_check
    CHECK (tipo_usuario IN ('adm', 'master', 'gestor', 'cliente'));
