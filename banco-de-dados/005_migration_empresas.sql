-- ============================================================
-- MIGRATION: Empresas e vínculo de gestor com empresa
-- Execute este arquivo no SQL Editor do Supabase.
-- Idempotente: usa IF NOT EXISTS.
-- ============================================================

CREATE TABLE IF NOT EXISTS empresas (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    razao_social VARCHAR(255) NOT NULL,
    nome_fantasia VARCHAR(255),
    cnpj VARCHAR(14) NOT NULL UNIQUE,
    ativo BOOLEAN DEFAULT TRUE,
    criado_em TIMESTAMPTZ DEFAULT NOW(),
    atualizado_em TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_empresas_razao_social ON empresas(razao_social);
CREATE INDEX IF NOT EXISTS idx_empresas_ativo ON empresas(ativo);

ALTER TABLE usuarios
    ADD COLUMN IF NOT EXISTS empresa_id UUID REFERENCES empresas(id);

CREATE INDEX IF NOT EXISTS idx_usuarios_empresa ON usuarios(empresa_id);

CREATE OR REPLACE FUNCTION validar_gestor_com_empresa()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.tipo_usuario = 'gestor' AND NEW.empresa_id IS NULL THEN
        RAISE EXCEPTION 'Gestor deve possuir empresa_id';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_validar_gestor_empresa ON usuarios;
CREATE TRIGGER trg_validar_gestor_empresa
    BEFORE INSERT OR UPDATE ON usuarios
    FOR EACH ROW EXECUTE FUNCTION validar_gestor_com_empresa();

