# Modulos do Repositorio

## Objetivo deste documento

Descrever o papel de cada pasta principal e orientar onde mexer quando surgir manutencao, correcao ou nova funcionalidade.

## `operacoes-goldcredit`

### Papel no sistema

Este e o modulo principal em desenvolvimento no Lovable. Ele concentra:

- frontend principal usado pelos times internos
- rotas protegidas e publicas
- integracao com Supabase
- edge functions de apoio
- interface de criacao e acompanhamento do fluxo de assinatura

### Stack principal

- React 18
- TypeScript
- Vite
- React Router
- TanStack Query
- Supabase JS
- Tailwind + shadcn/ui

### Rotas principais identificadas

- `/login`
- `/painel`
- `/consulta`
- `/cedente/:id`
- `/carteira/giro`
- `/carteira/metricas`
- `/carteira/gestao`
- `/clientes`
- `/clientes/:id`
- `/consultas`
- `/historico-serasa`
- `/historico-scr`
- `/historico-agrisk`
- `/perfil`
- `/contratos/documentos`
- `/contratos/documentos/:token`
- `/contratos/assinatura-digital`
- `/admin`
- `/assinar/:token`
- `/assinar-operacao/:token`

### Organizacao relevante

- `src/pages`: paginas da aplicacao
- `src/components`: componentes de interface e fluxos especificos
- `src/lib`: clientes e funcoes auxiliares de integracao
- `src/contexts`: contexto de autenticacao
- `src/integrations/supabase`: cliente e tipos do Supabase
- `supabase/functions`: edge functions

### Edge functions atualmente presentes

As seguintes funcoes foram identificadas no repositorio:

- `admin-users`
- `agrisk-query`
- `analyze-cedente`
- `analyze-client-summary`
- `analyze-document`
- `bootstrap-master`
- `cedente-info`
- `dashboard-data`
- `external-db`
- `giro-carteira`
- `goldsign-proxy`
- `goldsign-settings`
- `hbi-scr`
- `import-csv`
- `portfolio-data`
- `process-email-queue`
- `process-sql`
- `serasa-report`

### Observacao importante

Este modulo nao deve ser documentado apenas como "frontend". Para onboarding correto, ele deve ser descrito como:

> aplicacao principal desenvolvida no Lovable, contendo interface web e edge functions de apoio ao dominio operacional e ao fluxo de assinatura

## `backend`

### Papel no sistema

API principal para regras sensiveis de assinatura digital e gerenciamento de documentos.

### Responsabilidades

- autenticacao
- gestao de empresas, gestores e clientes
- upload e listagem de documentos
- criacao de solicitacoes de assinatura
- validacao de certificado
- preparo e submissao de assinatura
- download do PDF assinado
- auditoria

### Arquivos centrais

- `main.py`: composicao da API e rotas
- `auth.py`: autenticacao e dependencias de usuario
- `database.py`: acesso ao banco e storage
- `signature_service.py`: preparo e aplicacao da assinatura no PDF
- `config.py`: configuracao por variaveis de ambiente
- `schemas.py`: contratos de entrada e saida

## `app`

### Papel no sistema

Aplicativo local para assinatura digital na maquina do signatario.

### Responsabilidades

- listar certificados ICP-Brasil instalados
- suportar certificados A1 e A3
- gerar assinatura CMS/PKCS#7 localmente
- manter a chave privada fora do backend e do frontend

### Endpoints documentados no modulo

- `GET /api/status`
- `GET /api/certificados`
- `POST /api/assinar`
- `POST /api/verificar-certificado`

## `banco-de-dados`

### Papel no sistema

Concentra scripts SQL e referencia de evolucao do modelo de dados.

### Itens principais

- `001_schema.sql`: schema inicial
- `002_policies.sql`: politicas de acesso
- `003_seed.sql`: dados de apoio
- migrations numeradas adicionais
- `supabase_full.sql`: dump mais amplo do ambiente

### Entidades centrais

- `empresas`
- `usuarios`
- `documentos`
- `solicitacoes_assinatura`
- `assinaturas`
- `auditoria`
- `socios`

## Arquivos de apoio na raiz

### `docker-compose.yml`

Usado para apoio ao desenvolvimento local, especialmente PostgreSQL e backend.

### `ARQUITETURA.mermaid`

Diagrama de alto nivel do fluxo de assinatura.

### `render.yaml`

Arquivo de apoio para publicacao do backend.
