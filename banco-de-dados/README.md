# Banco de Dados - Assinatura Digital ICP-Brasil

## Supabase (Produção)

O sistema utiliza **PostgreSQL via Supabase** como banco de dados principal.

### Configuração

1. Crie um projeto no [Supabase](https://supabase.com)
2. Execute os scripts SQL na ordem:
   - `001_schema.sql` — Tabelas, índices, triggers e funções
   - `002_policies.sql` — Row Level Security para acesso direto
   - `003_seed.sql` — (Opcional) Dados de teste

3. Crie um bucket de Storage chamado `documentos-pdf` (privado)

4. Copie as credenciais para o `.env` do backend:
   - `SUPABASE_URL` → Settings > API > Project URL
   - `SUPABASE_SERVICE_KEY` → Settings > API > service_role key
   - `SUPABASE_DB_URL` → Settings > Database > Connection string (opcional, usada para inferir SUPABASE_URL)

### Tabelas

| Tabela | Descrição |
|--------|-----------|
| `usuarios` | Usuários do sistema (remetentes) |
| `documentos` | PDFs enviados para assinatura |
| `solicitacoes_assinatura` | Links seguros com token UUID e expiração |
| `assinaturas` | Registro das assinaturas digitais realizadas |
| `auditoria` | Log completo de eventos para rastreabilidade |

### Storage

Os PDFs são armazenados no Supabase Storage:
- Bucket: `documentos-pdf` (privado)
- Estrutura: `documentos/{usuario_id}/{uuid}/{nome_arquivo}.pdf`
- PDFs assinados: sufixo `_assinado.pdf`

### Desenvolvimento Local

Para desenvolvimento sem Supabase, use o `docker-compose.yml` na raiz
que sobe um PostgreSQL local na porta 5432.

```bash
docker-compose up postgres
```
