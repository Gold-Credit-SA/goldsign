# GoldSign

Sistema de operacao e assinatura digital com foco em:

- gestao de clientes, cedentes, carteira e consultas operacionais
- emissao e acompanhamento de solicitacoes de assinatura
- assinatura digital ICP-Brasil com certificados A1 e A3
- rastreabilidade de documentos, solicitacoes e auditoria

## Estrutura do repositorio

```text
GoldSign/
|-- operacoes-goldcredit/   # Frontend principal no Lovable + edge functions no Supabase
|-- backend/                # API FastAPI com regras de assinatura e autenticacao sensivel
|-- app/                    # Aplicativo local para acesso a certificados ICP-Brasil
|-- banco-de-dados/         # Schemas, policies, seeds e migrations SQL
|-- docs/                   # Documentacao principal do sistema
|-- docker-compose.yml      # Apoio a desenvolvimento local
`-- ARQUITETURA.mermaid     # Diagrama de alto nivel
```

## Como o sistema se divide

### `operacoes-goldcredit`

E o modulo que esta sendo desenvolvido no Lovable. Ele concentra:

- o frontend principal usado pelos times internos
- rotas autenticadas e publicas de operacao
- integracao com Supabase
- edge functions de apoio para CRUD, consultas e integracoes auxiliares
- interface de criacao e acompanhamento das solicitacoes de assinatura

### `backend`

Responsavel pelas regras sensiveis de assinatura:

- autenticacao e papeis de usuario
- upload e armazenamento de documentos
- geracao e validacao de links de assinatura
- preparo do PDF para assinatura externa
- aplicacao da assinatura CMS/PKCS#7 no PDF em padrao PAdES
- auditoria do fluxo

### `app`

Aplicativo local executado na maquina do signatario. Faz a ponte com os certificados ICP-Brasil instalados no sistema operacional ou em token/smartcard, sem expor a chave privada.

### `banco-de-dados`

Contem a referencia do modelo de dados e scripts SQL usados no projeto.

## Documentacao principal

Leia a documentacao em `docs/` na seguinte ordem:

1. [docs/visao-geral.md](./docs/visao-geral.md)
2. [docs/arquitetura.md](./docs/arquitetura.md)
3. [docs/modulos.md](./docs/modulos.md)
4. [docs/fluxos-principais.md](./docs/fluxos-principais.md)
5. [docs/backend-api.md](./docs/backend-api.md)
6. [docs/onboarding.md](./docs/onboarding.md)

## Fluxo resumido de assinatura

1. Um usuario interno cria a solicitacao pelo frontend `operacoes-goldcredit`.
2. O `backend` recebe os documentos, registra metadados e gera links/token de assinatura.
3. O signatario acessa o link publico no frontend.
4. O frontend conversa com o `app` local em `http://localhost:8765`.
5. O `app` lista certificados e gera a assinatura local com a chave privada.
6. O frontend envia a assinatura CMS para o `backend`.
7. O `backend` aplica a assinatura PAdES ao PDF e registra auditoria.

## Referencias rapidas

- Diagrama tecnico: [ARQUITETURA.mermaid](./ARQUITETURA.mermaid)
- Backend deploy: [backend/DEPLOY_RENDER.md](./backend/DEPLOY_RENDER.md)
- App local: [app/README.md](./app/README.md)
- Banco: [banco-de-dados/README.md](./banco-de-dados/README.md)
