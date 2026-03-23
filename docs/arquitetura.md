# Arquitetura

## Visao de alto nivel

O sistema e composto por quatro blocos principais:

1. `operacoes-goldcredit`
2. `backend`
3. `app`
4. `banco-de-dados`

Cada bloco tem uma responsabilidade bem definida e roda em um ambiente diferente.

## Onde cada parte roda

### `operacoes-goldcredit`

- roda como aplicacao web
- e desenvolvido no Lovable
- usa React + TypeScript + Vite
- integra com Supabase e com o backend de assinatura
- contem edge functions no diretorio `supabase/functions`

### `backend`

- roda como servico HTTP em FastAPI
- pode ser publicado separadamente
- no estado atual, ha material de deploy para Render
- concentra regras de assinatura e API sensivel

### `app`

- roda localmente na maquina do signatario
- expoe API HTTP local em `http://localhost:8765`
- acessa certificados instalados no sistema operacional ou em token/smartcard

### `banco-de-dados`

- o ambiente principal usa Supabase
- existe apoio local com PostgreSQL via `docker-compose.yml`
- armazena usuarios, empresas, documentos, solicitacoes, assinaturas e auditoria

## Responsabilidades por modulo

### Frontend Lovable (`operacoes-goldcredit`)

Responsabilidades:

- autenticar usuarios
- exibir telas de operacao
- acionar edge functions de apoio
- consumir backend de assinatura
- interagir com o app local durante o fluxo publico de assinatura

Nao deve concentrar:

- regra criptografica sensivel
- aplicacao final da assinatura no PDF
- logica que depende de segredo de servidor

### Backend de assinatura (`backend`)

Responsabilidades:

- emitir tokens e validar acesso
- registrar documentos e solicitacoes
- controlar expiracao e estado de assinatura
- preparar PDF para assinatura externa
- validar certificado do signatario
- aplicar assinatura CMS ao PDF no padrao PAdES
- registrar auditoria

### Assinador local (`app`)

Responsabilidades:

- listar certificados disponiveis
- validar certificado na maquina local
- assinar localmente o hash recebido
- nunca expor a chave privada para o frontend ou backend

## Integracoes importantes

### Integracao entre frontend e backend

O frontend usa `VITE_BACKEND_URL` para consumir o backend principal. Rotas publicas de assinatura e criacao de solicitacao passam por essa integracao.

### Integracao entre frontend e app local

O frontend usa `VITE_LOCAL_SIGNER_URL` para conversar com o aplicativo local. No estado atual, o valor padrao e `http://localhost:8765`.

### Integracao entre frontend e Supabase

O frontend usa:

- `VITE_SUPABASE_URL`
- `VITE_SUPABASE_PUBLISHABLE_KEY`

Essas variaveis sao usadas para autenticacao, acesso ao Supabase e chamadas para edge functions.

### Integracao entre backend e Supabase

O backend depende de:

- `SUPABASE_URL`
- `SUPABASE_SERVICE_KEY`
- `SUPABASE_DB_URL` opcional

Sem essas variaveis, o backend nao sobe corretamente.

## Modelo de comunicacao

### Fluxo operacional interno

`Usuario interno -> operacoes-goldcredit -> Supabase/edge functions`

### Fluxo de assinatura digital

`Usuario interno -> operacoes-goldcredit -> backend -> Supabase`

`Signatario -> operacoes-goldcredit -> app local -> operacoes-goldcredit -> backend -> Supabase`

## Dependencias externas relevantes

- Supabase
- Render no fluxo atual de deploy do backend
- certificados ICP-Brasil A1/A3
- pyHanko no backend para assinatura PAdES

## Tabelas principais do banco

As tabelas principais identificadas em `banco-de-dados/001_schema.sql` sao:

- `empresas`
- `usuarios`
- `documentos`
- `solicitacoes_assinatura`
- `assinaturas`
- `auditoria`

No dump completo tambem existe `socios`, usado no contexto de vinculo de assinatura.

## Diagrama

O diagrama de referencia do sistema esta em `ARQUITETURA.mermaid`. Sempre que houver mudanca estrutural relevante, este arquivo deve ser atualizado junto com esta documentacao.
