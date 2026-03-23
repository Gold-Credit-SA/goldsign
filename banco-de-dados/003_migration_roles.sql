-- ============================================================
-- MIGRATION: Sistema de roles (adm, gestor, cliente)
-- Execute este arquivo no SQL Editor do Supabase.
-- Seguro para rodar em instâncias existentes (usa IF NOT EXISTS).
-- ============================================================

-- ============================================================
-- PARTE 1: Novas colunas nas tabelas existentes
-- ============================================================

-- Adiciona tipo_usuario na tabela usuarios
-- Usuários já existentes receberão 'gestor' como valor padrão
ALTER TABLE usuarios
    ADD COLUMN IF NOT EXISTS tipo_usuario VARCHAR(10) NOT NULL DEFAULT 'gestor'
        CHECK (tipo_usuario IN ('adm', 'master', 'gestor', 'cliente'));

-- Adiciona gestor_id: para clientes, indica quem os criou
ALTER TABLE usuarios
    ADD COLUMN IF NOT EXISTS gestor_id UUID REFERENCES usuarios(id);

-- Adiciona cliente_id em solicitacoes_assinatura
-- Vincula a solicitação à conta do cliente no sistema
ALTER TABLE solicitacoes_assinatura
    ADD COLUMN IF NOT EXISTS cliente_id UUID REFERENCES usuarios(id);

-- ============================================================
-- PARTE 2: Índices
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_usuarios_tipo        ON usuarios(tipo_usuario);
CREATE INDEX IF NOT EXISTS idx_usuarios_gestor      ON usuarios(gestor_id);
CREATE INDEX IF NOT EXISTS idx_solicitacoes_cliente ON solicitacoes_assinatura(cliente_id);

-- CPF (11 dígitos) ou CNPJ (14 dígitos) para autenticação por certificado digital
ALTER TABLE usuarios
    ADD COLUMN IF NOT EXISTS cpf_cnpj VARCHAR(14);

CREATE UNIQUE INDEX IF NOT EXISTS idx_usuarios_cpf_cnpj
    ON usuarios(cpf_cnpj) WHERE cpf_cnpj IS NOT NULL;

-- ============================================================
-- PARTE 3: Atualizar políticas RLS
-- Remove as políticas antigas e cria as novas com suporte a roles
-- ============================================================

-- Remover políticas antigas (nomes do schema anterior)
DROP POLICY IF EXISTS "documentos_select_remetente"   ON documentos;
DROP POLICY IF EXISTS "documentos_insert_remetente"   ON documentos;
DROP POLICY IF EXISTS "solicitacoes_select_remetente" ON solicitacoes_assinatura;
DROP POLICY IF EXISTS "assinaturas_select_remetente"  ON assinaturas;

-- Remover políticas novas caso já existam (idempotente)
DROP POLICY IF EXISTS "documentos_select_gestor"      ON documentos;
DROP POLICY IF EXISTS "documentos_insert_gestor"      ON documentos;
DROP POLICY IF EXISTS "solicitacoes_select_gestor"    ON solicitacoes_assinatura;
DROP POLICY IF EXISTS "solicitacoes_select_cliente"   ON solicitacoes_assinatura;
DROP POLICY IF EXISTS "assinaturas_select_gestor"     ON assinaturas;
DROP POLICY IF EXISTS "assinaturas_select_cliente"    ON assinaturas;

-- Política: usuários veem apenas seu próprio perfil (inalterada)
DROP POLICY IF EXISTS "usuarios_select_proprio" ON usuarios;
CREATE POLICY "usuarios_select_proprio"
    ON usuarios FOR SELECT
    USING (auth.uid()::text = id::text);

-- Política: gestor vê apenas seus documentos
CREATE POLICY "documentos_select_gestor"
    ON documentos FOR SELECT
    USING (remetente_id::text = auth.uid()::text);

-- Política: gestor pode inserir documentos
CREATE POLICY "documentos_insert_gestor"
    ON documentos FOR INSERT
    WITH CHECK (remetente_id::text = auth.uid()::text);

-- Política: gestor vê solicitações dos seus documentos
CREATE POLICY "solicitacoes_select_gestor"
    ON solicitacoes_assinatura FOR SELECT
    USING (
        documento_id IN (
            SELECT id FROM documentos
            WHERE remetente_id::text = auth.uid()::text
        )
    );

-- Política: cliente vê apenas suas próprias solicitações
CREATE POLICY "solicitacoes_select_cliente"
    ON solicitacoes_assinatura FOR SELECT
    USING (cliente_id::text = auth.uid()::text);

-- Política: gestor vê assinaturas dos seus documentos
CREATE POLICY "assinaturas_select_gestor"
    ON assinaturas FOR SELECT
    USING (
        documento_id IN (
            SELECT id FROM documentos
            WHERE remetente_id::text = auth.uid()::text
        )
    );

-- Política: cliente vê assinaturas dos contratos que assinou
CREATE POLICY "assinaturas_select_cliente"
    ON assinaturas FOR SELECT
    USING (
        solicitacao_id IN (
            SELECT id FROM solicitacoes_assinatura
            WHERE cliente_id::text = auth.uid()::text
        )
    );

-- Auditoria: sem acesso direto (inalterada)
DROP POLICY IF EXISTS "auditoria_nenhum_acesso_direto" ON auditoria;
CREATE POLICY "auditoria_nenhum_acesso_direto"
    ON auditoria FOR SELECT
    USING (false);
