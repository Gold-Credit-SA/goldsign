-- ============================================================
-- POLÍTICAS DE SEGURANÇA (Row Level Security - Supabase)
-- Sistema com 3 roles: adm, gestor, cliente
-- ============================================================

-- Habilitar RLS em todas as tabelas
ALTER TABLE usuarios ENABLE ROW LEVEL SECURITY;
ALTER TABLE documentos ENABLE ROW LEVEL SECURITY;
ALTER TABLE solicitacoes_assinatura ENABLE ROW LEVEL SECURITY;
ALTER TABLE assinaturas ENABLE ROW LEVEL SECURITY;
ALTER TABLE auditoria ENABLE ROW LEVEL SECURITY;

-- ============================================================
-- Nota: O backend usa a service_role key do Supabase, que
-- bypassa o RLS automaticamente. As políticas abaixo são para
-- acesso direto via Supabase client (anon/authenticated).
-- ============================================================

-- Usuários podem ver seu próprio perfil
CREATE POLICY "usuarios_select_proprio"
    ON usuarios FOR SELECT
    USING (auth.uid()::text = id::text);

-- Gestor pode ver seus próprios documentos
CREATE POLICY "documentos_select_gestor"
    ON documentos FOR SELECT
    USING (remetente_id::text = auth.uid()::text);

-- Gestor pode inserir documentos
CREATE POLICY "documentos_insert_gestor"
    ON documentos FOR INSERT
    WITH CHECK (remetente_id::text = auth.uid()::text);

-- Gestor pode ver solicitações dos seus documentos
CREATE POLICY "solicitacoes_select_gestor"
    ON solicitacoes_assinatura FOR SELECT
    USING (
        documento_id IN (
            SELECT id FROM documentos WHERE remetente_id::text = auth.uid()::text
        )
    );

-- Cliente pode ver suas próprias solicitações
CREATE POLICY "solicitacoes_select_cliente"
    ON solicitacoes_assinatura FOR SELECT
    USING (cliente_id::text = auth.uid()::text);

-- Assinaturas visíveis para o gestor do documento
CREATE POLICY "assinaturas_select_gestor"
    ON assinaturas FOR SELECT
    USING (
        documento_id IN (
            SELECT id FROM documentos WHERE remetente_id::text = auth.uid()::text
        )
    );

-- Assinaturas visíveis para o cliente que assinou
CREATE POLICY "assinaturas_select_cliente"
    ON assinaturas FOR SELECT
    USING (
        solicitacao_id IN (
            SELECT id FROM solicitacoes_assinatura
            WHERE cliente_id::text = auth.uid()::text
        )
    );

-- Auditoria visível apenas via backend (service_role)
CREATE POLICY "auditoria_nenhum_acesso_direto"
    ON auditoria FOR SELECT
    USING (false);

-- ============================================================
-- Criar bucket de storage para PDFs
-- (Executar via Supabase Dashboard ou API)
-- ============================================================
-- INSERT INTO storage.buckets (id, name, public)
-- VALUES ('documentos-pdf', 'documentos-pdf', false);

-- Política de storage: apenas backend (service_role) acessa
-- INSERT INTO storage.policies (bucket_id, name, definition)
-- VALUES ('documentos-pdf', 'service_role_only', '{"role": "service_role"}');
