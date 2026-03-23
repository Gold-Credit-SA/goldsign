-- ============================================================
-- SEED: Dados iniciais para desenvolvimento
-- ============================================================

-- Nota: Em produÃ§Ã£o, nÃ£o executar este arquivo.
-- Use o endpoint /api/setup/primeiro-admin para criar o adm inicial.
-- As senhas abaixo sÃ£o apenas para teste (hash de "123456").

-- UsuÃ¡rio adm de teste
INSERT INTO usuarios (id, email, nome, senha_hash, tipo_usuario) VALUES
    ('00000000-0000-0000-0000-000000000001',
     'admin@teste.com',
     'Administrador Teste',
     '$2b$12$LJ3m4YsGJfXxr3rV1qXJXeJ3Py5H8jKF6XZsHqX9vYn1xIq4Z2LNa',
     'adm')
ON CONFLICT (email) DO NOTHING;

-- Empresa de teste
INSERT INTO empresas (id, razao_social, nome_fantasia, cnpj) VALUES
    ('10000000-0000-0000-0000-000000000001',
     'Empresa Teste LTDA',
     'Empresa Teste',
     '12345678000190')
ON CONFLICT (cnpj) DO NOTHING;

-- Gestor de teste
INSERT INTO usuarios (id, email, nome, senha_hash, tipo_usuario, empresa_id) VALUES
    ('00000000-0000-0000-0000-000000000002',
     'gestor@teste.com',
     'Gestor Teste',
     '$2b$12$LJ3m4YsGJfXxr3rV1qXJXeJ3Py5H8jKF6XZsHqX9vYn1xIq4Z2LNa',
     'gestor',
     '10000000-0000-0000-0000-000000000001')
ON CONFLICT (email) DO NOTHING;

-- Cliente de teste (criado pelo gestor acima)
INSERT INTO usuarios (id, email, nome, senha_hash, tipo_usuario, gestor_id) VALUES
    ('00000000-0000-0000-0000-000000000003',
     'cliente@teste.com',
     'Cliente Teste',
     '$2b$12$LJ3m4YsGJfXxr3rV1qXJXeJ3Py5H8jKF6XZsHqX9vYn1xIq4Z2LNa',
     'cliente',
     '00000000-0000-0000-0000-000000000002')
ON CONFLICT (email) DO NOTHING;



