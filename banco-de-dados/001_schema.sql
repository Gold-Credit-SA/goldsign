-- ============================================================
-- ASSINATURA DIGITAL ICP-BRASIL
-- Schema principal do banco de dados (Supabase/PostgreSQL)
-- ============================================================

-- ExtensÃµes necessÃ¡rias
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================
-- TABELA: empresas
-- Empresas cadastradas pelo administrador
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

CREATE INDEX idx_empresas_razao_social ON empresas(razao_social);
CREATE INDEX idx_empresas_ativo ON empresas(ativo);
-- ============================================================
-- TABELA: usuarios
-- UsuÃ¡rios do sistema (adm, gestor, cliente)
-- ============================================================
CREATE TABLE IF NOT EXISTS usuarios (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) NOT NULL UNIQUE,
    nome VARCHAR(255) NOT NULL,
    senha_hash VARCHAR(255) NOT NULL,
    tipo_usuario VARCHAR(10) NOT NULL DEFAULT 'gestor'
        CHECK (tipo_usuario IN ('adm', 'master', 'gestor', 'cliente')),
    gestor_id UUID REFERENCES usuarios(id),  -- para clientes: quem os criou
    empresa_id UUID REFERENCES empresas(id), -- para gestores: empresa vinculada
    avatar_url TEXT,
    ativo BOOLEAN DEFAULT TRUE,
    criado_em TIMESTAMPTZ DEFAULT NOW(),
    atualizado_em TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_usuarios_email ON usuarios(email);
CREATE INDEX idx_usuarios_tipo ON usuarios(tipo_usuario);
CREATE INDEX idx_usuarios_gestor ON usuarios(gestor_id);
CREATE INDEX idx_usuarios_empresa ON usuarios(empresa_id);

-- ============================================================
-- TABELA: documentos
-- Documentos PDF enviados para assinatura
-- ============================================================
CREATE TABLE IF NOT EXISTS documentos (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    titulo VARCHAR(500) NOT NULL,
    nome_arquivo VARCHAR(500) NOT NULL,
    tamanho_bytes BIGINT NOT NULL,
    hash_sha256 VARCHAR(64) NOT NULL,
    storage_path VARCHAR(1000) NOT NULL,
    storage_path_assinado VARCHAR(1000),
    remetente_id UUID NOT NULL REFERENCES usuarios(id),
    status VARCHAR(50) DEFAULT 'pendente'
        CHECK (status IN ('pendente', 'aguardando_assinatura', 'assinado', 'expirado', 'cancelado')),
    criado_em TIMESTAMPTZ DEFAULT NOW(),
    atualizado_em TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_documentos_remetente ON documentos(remetente_id);
CREATE INDEX idx_documentos_status ON documentos(status);

-- ============================================================
-- TABELA: solicitacoes_assinatura
-- Links seguros para assinatura de documentos
-- ============================================================
CREATE TABLE IF NOT EXISTS solicitacoes_assinatura (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    documento_id UUID NOT NULL REFERENCES documentos(id) ON DELETE CASCADE,
    token_acesso UUID NOT NULL DEFAULT uuid_generate_v4() UNIQUE,
    signatario_email VARCHAR(255) NOT NULL,
    signatario_nome VARCHAR(255),
    cliente_id UUID REFERENCES usuarios(id),  -- conta do cliente no sistema
    mensagem TEXT,
    assinatura_pagina INTEGER NOT NULL DEFAULT 1,
    assinatura_x NUMERIC(6,5) NOT NULL DEFAULT 0.06,
    assinatura_y NUMERIC(6,5) NOT NULL DEFAULT 0.06,
    assinatura_largura NUMERIC(6,5) NOT NULL DEFAULT 0.44,
    assinatura_altura NUMERIC(6,5) NOT NULL DEFAULT 0.12,
    status VARCHAR(50) DEFAULT 'pendente'
        CHECK (status IN ('pendente', 'visualizado', 'assinado', 'expirado', 'recusado')),
    expira_em TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '7 days'),
    visualizado_em TIMESTAMPTZ,
    assinado_em TIMESTAMPTZ,
    criado_em TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_solicitacoes_token ON solicitacoes_assinatura(token_acesso);
CREATE INDEX idx_solicitacoes_documento ON solicitacoes_assinatura(documento_id);
CREATE INDEX idx_solicitacoes_status ON solicitacoes_assinatura(status);
CREATE INDEX idx_solicitacoes_cliente ON solicitacoes_assinatura(cliente_id);

-- ============================================================
-- TABELA: assinaturas
-- Registro de assinaturas digitais realizadas
-- ============================================================
CREATE TABLE IF NOT EXISTS assinaturas (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    solicitacao_id UUID NOT NULL REFERENCES solicitacoes_assinatura(id),
    documento_id UUID NOT NULL REFERENCES documentos(id),
    
    -- Dados do certificado (informaÃ§Ãµes pÃºblicas)
    cert_subject_cn VARCHAR(500),
    cert_subject_cpf VARCHAR(14),
    cert_issuer_cn VARCHAR(500),
    cert_serial_number VARCHAR(100),
    cert_not_before TIMESTAMPTZ,
    cert_not_after TIMESTAMPTZ,
    cert_tipo VARCHAR(10) CHECK (cert_tipo IN ('A1', 'A3')),
    cert_pem TEXT,
    
    -- Dados da assinatura
    assinatura_cms BYTEA,
    hash_conteudo_assinado VARCHAR(64),
    algoritmo_assinatura VARCHAR(50) DEFAULT 'SHA256withRSA',
    
    -- Metadados
    ip_signatario INET,
    user_agent TEXT,
    
    criado_em TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_assinaturas_solicitacao ON assinaturas(solicitacao_id);
CREATE INDEX idx_assinaturas_documento ON assinaturas(documento_id);
CREATE INDEX idx_assinaturas_cpf ON assinaturas(cert_subject_cpf);

-- ============================================================
-- TABELA: auditoria
-- Log de auditoria para rastreabilidade
-- ============================================================
CREATE TABLE IF NOT EXISTS auditoria (
    id BIGSERIAL PRIMARY KEY,
    tipo_evento VARCHAR(100) NOT NULL,
    documento_id UUID REFERENCES documentos(id),
    solicitacao_id UUID REFERENCES solicitacoes_assinatura(id),
    usuario_id UUID REFERENCES usuarios(id),
    descricao TEXT NOT NULL,
    dados_extras JSONB,
    ip_origem INET,
    user_agent TEXT,
    criado_em TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_auditoria_documento ON auditoria(documento_id);
CREATE INDEX idx_auditoria_tipo ON auditoria(tipo_evento);
CREATE INDEX idx_auditoria_criado ON auditoria(criado_em DESC);

-- ============================================================
-- FUNÃ‡ÃƒO: Atualizar timestamp de atualizaÃ§Ã£o
-- ============================================================
CREATE OR REPLACE FUNCTION atualizar_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.atualizado_em = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_usuarios_atualizado
    BEFORE UPDATE ON usuarios
    FOR EACH ROW EXECUTE FUNCTION atualizar_timestamp();

CREATE TRIGGER trg_documentos_atualizado
    BEFORE UPDATE ON documentos
    FOR EACH ROW EXECUTE FUNCTION atualizar_timestamp();

-- ============================================================
-- FUNÃ‡ÃƒO: Verificar expiraÃ§Ã£o de solicitaÃ§Ãµes
-- ============================================================
CREATE OR REPLACE FUNCTION expirar_solicitacoes()
RETURNS INTEGER AS $$
DECLARE
    total INTEGER;
BEGIN
    UPDATE solicitacoes_assinatura
    SET status = 'expirado'
    WHERE status IN ('pendente', 'visualizado')
      AND expira_em < NOW();
    
    GET DIAGNOSTICS total = ROW_COUNT;
    
    UPDATE documentos d
    SET status = 'expirado'
    WHERE d.id IN (
        SELECT DISTINCT documento_id
        FROM solicitacoes_assinatura
        WHERE status = 'expirado'
    )
    AND d.status = 'aguardando_assinatura'
    AND NOT EXISTS (
        SELECT 1 FROM solicitacoes_assinatura s
        WHERE s.documento_id = d.id
        AND s.status IN ('pendente', 'visualizado')
    );
    
    RETURN total;
END;
$$ LANGUAGE plpgsql;



