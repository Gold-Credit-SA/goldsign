-- ============================================================
-- MIGRATION: vinculos de cliente + assinante obrigatorio
-- Execute este arquivo no SQL Editor do Supabase.
-- ============================================================

BEGIN;

-- ------------------------------------------------------------
-- socios: evolui para tabela de vinculados (socio / responsavel_solidario)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS socios (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cliente_id UUID NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    cpf VARCHAR(11),
    nome VARCHAR(255),
    criado_em TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE socios
    ADD COLUMN IF NOT EXISTS cpf VARCHAR(11);

ALTER TABLE socios
    ADD COLUMN IF NOT EXISTS nome VARCHAR(255);

ALTER TABLE socios
    ADD COLUMN IF NOT EXISTS criado_em TIMESTAMPTZ DEFAULT now();

ALTER TABLE socios
    ADD COLUMN IF NOT EXISTS cpf_cnpj VARCHAR(14);

ALTER TABLE socios
    ADD COLUMN IF NOT EXISTS email VARCHAR(255);

ALTER TABLE socios
    ADD COLUMN IF NOT EXISTS tipo_vinculo VARCHAR(30) NOT NULL DEFAULT 'socio';

-- migra dados antigos
UPDATE socios
SET cpf_cnpj = cpf
WHERE cpf_cnpj IS NULL AND cpf IS NOT NULL;

-- constraint de tipo
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'socios_tipo_vinculo_check'
    ) THEN
        ALTER TABLE socios DROP CONSTRAINT socios_tipo_vinculo_check;
    END IF;
END $$;

ALTER TABLE socios
    ADD CONSTRAINT socios_tipo_vinculo_check
    CHECK (tipo_vinculo IN ('socio', 'responsavel_solidario'));

-- cpf_cnpj passa a ser obrigatorio
ALTER TABLE socios
    ALTER COLUMN cpf_cnpj SET NOT NULL;

ALTER TABLE socios
    ALTER COLUMN cpf DROP NOT NULL;

-- remove indice legado para permitir cpf/cnpj de 11 ou 14 e regra por cliente
DROP INDEX IF EXISTS idx_socios_cpf;

CREATE INDEX IF NOT EXISTS idx_socios_cpf_cnpj
    ON socios(cpf_cnpj);

CREATE UNIQUE INDEX IF NOT EXISTS idx_socios_cliente_doc_tipo_unico
    ON socios(cliente_id, cpf_cnpj, tipo_vinculo);

-- ------------------------------------------------------------
-- solicitacoes_assinatura: metadados de assinante obrigatorio
-- ------------------------------------------------------------
ALTER TABLE solicitacoes_assinatura
    ADD COLUMN IF NOT EXISTS assinatura_obrigatoria_tipo VARCHAR(30);

ALTER TABLE solicitacoes_assinatura
    ADD COLUMN IF NOT EXISTS assinatura_obrigatoria_cpf_cnpj VARCHAR(14);

ALTER TABLE solicitacoes_assinatura
    ADD COLUMN IF NOT EXISTS assinatura_obrigatoria_nome VARCHAR(255);

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'solicitacoes_assinatura_obrigatoria_tipo_check'
    ) THEN
        ALTER TABLE solicitacoes_assinatura
            DROP CONSTRAINT solicitacoes_assinatura_obrigatoria_tipo_check;
    END IF;
END $$;

ALTER TABLE solicitacoes_assinatura
    ADD CONSTRAINT solicitacoes_assinatura_obrigatoria_tipo_check
    CHECK (
        assinatura_obrigatoria_tipo IS NULL
        OR assinatura_obrigatoria_tipo IN (
            'cliente_cpf',
            'cliente_cnpj',
            'socio',
            'responsavel_solidario'
        )
    );

CREATE INDEX IF NOT EXISTS idx_solicitacoes_assinatura_obrigatoria_doc
    ON solicitacoes_assinatura(assinatura_obrigatoria_cpf_cnpj);

COMMIT;




