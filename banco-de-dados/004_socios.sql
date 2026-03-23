-- ============================================================
-- MIGRATION: Tabela de sócios por cliente
-- Execute este arquivo no SQL Editor do Supabase.
-- Cria tabela socios para vincular CPFs de sócios a clientes CNPJ.
-- ============================================================

CREATE TABLE IF NOT EXISTS socios (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cliente_id  UUID NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    cpf         VARCHAR(11) NOT NULL,
    nome        VARCHAR(255),
    criado_em   TIMESTAMPTZ DEFAULT now()
);

-- CPF de sócio é único globalmente (um CPF só pode ser sócio de um cliente)
CREATE UNIQUE INDEX IF NOT EXISTS idx_socios_cpf       ON socios(cpf);
CREATE INDEX        IF NOT EXISTS idx_socios_cliente_id ON socios(cliente_id);

-- ============================================================
-- RLS (o backend usa service_role key — bypassa RLS)
-- Habilitamos RLS mas deixamos o acesso controlado pelo backend.
-- ============================================================
ALTER TABLE socios ENABLE ROW LEVEL SECURITY;

-- Nenhum acesso direto via cliente — apenas via service_role do backend
DROP POLICY IF EXISTS "socios_sem_acesso_direto" ON socios;
CREATE POLICY "socios_sem_acesso_direto"
    ON socios FOR ALL
    USING (false);
