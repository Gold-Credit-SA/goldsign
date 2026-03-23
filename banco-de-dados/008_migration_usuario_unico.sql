-- ============================================================
-- MIGRATION: simplificacao para usuario unico (sem gestor/cliente)
-- Execute este arquivo no SQL Editor do Supabase.
--
-- Objetivo:
-- 1) remover estruturas antigas de gestor/cliente
-- 2) manter somente role "usuario"
-- 3) garantir que todo usuario esteja vinculado a uma empresa
-- 4) suportar cadastro como empresa, MEI ou autonomo
-- ============================================================

BEGIN;

-- ============================================================
-- 1) empresas: suporte a tipo de cadastro
-- ============================================================
ALTER TABLE empresas
    ADD COLUMN IF NOT EXISTS tipo_cadastro VARCHAR(20);

ALTER TABLE empresas
    ADD COLUMN IF NOT EXISTS documento VARCHAR(14);

-- cnpj deixa de ser obrigatorio (autonomo pode usar CPF)
DO $$
BEGIN
    BEGIN
        ALTER TABLE empresas ALTER COLUMN cnpj DROP NOT NULL;
    EXCEPTION WHEN others THEN
        NULL;
    END;
END $$;

-- normaliza tipo_cadastro para registros antigos
UPDATE empresas
SET tipo_cadastro = 'empresa'
WHERE tipo_cadastro IS NULL;

-- constraint de tipo (idempotente)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'empresas_tipo_cadastro_check'
    ) THEN
        ALTER TABLE empresas DROP CONSTRAINT empresas_tipo_cadastro_check;
    END IF;
END $$;

ALTER TABLE empresas
    ADD CONSTRAINT empresas_tipo_cadastro_check
    CHECK (tipo_cadastro IN ('empresa', 'mei', 'autonomo'));

-- indice unico para documento quando informado
CREATE UNIQUE INDEX IF NOT EXISTS idx_empresas_documento
    ON empresas(documento) WHERE documento IS NOT NULL;

-- ============================================================
-- 2) usuarios: role unica e vinculo obrigatorio com empresa
-- ============================================================
-- remove trigger/fn de validacao antiga (gestor)
DROP TRIGGER IF EXISTS trg_validar_gestor_empresa ON usuarios;
DROP FUNCTION IF EXISTS validar_gestor_com_empresa();

-- garante empresa para usuarios que nao tinham vinculo
DO $$
DECLARE
    u RECORD;
    nova_empresa_id UUID;
BEGIN
    FOR u IN
        SELECT id, nome, cpf_cnpj
        FROM usuarios
        WHERE empresa_id IS NULL
    LOOP
        INSERT INTO empresas (razao_social, nome_fantasia, cnpj, tipo_cadastro, documento, ativo)
        VALUES (
            COALESCE(NULLIF(TRIM(u.nome), ''), 'Conta sem nome'),
            COALESCE(NULLIF(TRIM(u.nome), ''), 'Conta sem nome'),
            NULL,
            CASE
                WHEN length(COALESCE(u.cpf_cnpj, '')) = 11 THEN 'autonomo'
                WHEN length(COALESCE(u.cpf_cnpj, '')) = 14 THEN 'empresa'
                ELSE 'autonomo'
            END,
            CASE
                WHEN length(COALESCE(u.cpf_cnpj, '')) IN (11, 14) THEN u.cpf_cnpj
                ELSE NULL
            END,
            TRUE
        )
        RETURNING id INTO nova_empresa_id;

        UPDATE usuarios
        SET empresa_id = nova_empresa_id
        WHERE id = u.id;
    END LOOP;
END $$;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'usuarios_tipo_usuario_check'
    ) THEN
        ALTER TABLE usuarios DROP CONSTRAINT usuarios_tipo_usuario_check;
    END IF;
END $$;

ALTER TABLE usuarios
    ADD CONSTRAINT usuarios_tipo_usuario_check
    CHECK (tipo_usuario IN ('adm', 'master', 'gestor', 'cliente', 'usuario'));

-- role unica
UPDATE usuarios
SET tipo_usuario = 'usuario'
WHERE tipo_usuario IS DISTINCT FROM 'usuario';

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'usuarios_tipo_usuario_check'
    ) THEN
        ALTER TABLE usuarios DROP CONSTRAINT usuarios_tipo_usuario_check;
    END IF;
END $$;

ALTER TABLE usuarios
    ADD CONSTRAINT usuarios_tipo_usuario_check
    CHECK (tipo_usuario IN ('usuario'));

ALTER TABLE usuarios
    ALTER COLUMN tipo_usuario SET DEFAULT 'usuario';

-- empresa_id passa a ser obrigatorio
ALTER TABLE usuarios
    ALTER COLUMN empresa_id SET NOT NULL;

-- remove coluna obsoleta de hierarquia gestor->cliente
ALTER TABLE usuarios
    DROP COLUMN IF EXISTS gestor_id;

DROP INDEX IF EXISTS idx_usuarios_gestor;

-- trigger novo: todo usuario deve ter empresa_id
CREATE OR REPLACE FUNCTION validar_usuario_com_empresa()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.empresa_id IS NULL THEN
        RAISE EXCEPTION 'Usuario deve possuir empresa_id';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_validar_usuario_empresa ON usuarios;
CREATE TRIGGER trg_validar_usuario_empresa
    BEFORE INSERT OR UPDATE ON usuarios
    FOR EACH ROW EXECUTE FUNCTION validar_usuario_com_empresa();

-- ============================================================
-- 3) remover policies legadas que dependem de cliente_id
-- (precisa vir antes de dropar a coluna)
-- ============================================================
DROP POLICY IF EXISTS "solicitacoes_select_cliente" ON solicitacoes_assinatura;
DROP POLICY IF EXISTS "assinaturas_select_cliente" ON assinaturas;

-- ============================================================
-- 4) remove estruturas de cliente interno
-- ============================================================
ALTER TABLE solicitacoes_assinatura
    DROP COLUMN IF EXISTS cliente_id;

DROP INDEX IF EXISTS idx_solicitacoes_cliente;

DROP TABLE IF EXISTS socios;

-- ============================================================
-- 5) RLS: politicas simplificadas para usuario dono
-- ============================================================
DROP POLICY IF EXISTS "usuarios_select_proprio" ON usuarios;
DROP POLICY IF EXISTS "documentos_select_gestor" ON documentos;
DROP POLICY IF EXISTS "documentos_insert_gestor" ON documentos;
DROP POLICY IF EXISTS "solicitacoes_select_gestor" ON solicitacoes_assinatura;
DROP POLICY IF EXISTS "assinaturas_select_gestor" ON assinaturas;
DROP POLICY IF EXISTS "auditoria_nenhum_acesso_direto" ON auditoria;

CREATE POLICY "usuarios_select_proprio"
    ON usuarios FOR SELECT
    USING (auth.uid()::text = id::text);

CREATE POLICY "documentos_select_owner"
    ON documentos FOR SELECT
    USING (remetente_id::text = auth.uid()::text);

CREATE POLICY "documentos_insert_owner"
    ON documentos FOR INSERT
    WITH CHECK (remetente_id::text = auth.uid()::text);

CREATE POLICY "documentos_update_owner"
    ON documentos FOR UPDATE
    USING (remetente_id::text = auth.uid()::text);

CREATE POLICY "solicitacoes_select_owner"
    ON solicitacoes_assinatura FOR SELECT
    USING (
        documento_id IN (
            SELECT id
            FROM documentos
            WHERE remetente_id::text = auth.uid()::text
        )
    );

CREATE POLICY "assinaturas_select_owner"
    ON assinaturas FOR SELECT
    USING (
        documento_id IN (
            SELECT id
            FROM documentos
            WHERE remetente_id::text = auth.uid()::text
        )
    );

CREATE POLICY "auditoria_nenhum_acesso_direto"
    ON auditoria FOR SELECT
    USING (false);

COMMIT;

-- ============================================================
-- OPCIONAL (manual): limpar registros antigos que nao fizerem mais sentido
-- Use com cuidado, somente se quiser reset operacional.
-- ============================================================
-- DELETE FROM auditoria;
-- DELETE FROM assinaturas;
-- DELETE FROM solicitacoes_assinatura;
-- DELETE FROM documentos;
-- DELETE FROM usuarios WHERE tipo_usuario = 'usuario' AND ativo = false;
