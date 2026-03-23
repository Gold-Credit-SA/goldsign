# Onboarding

## Objetivo

Fazer uma pessoa nova conseguir entender a arquitetura e subir o ambiente local com o menor atrito possivel.

## Leitura recomendada no primeiro dia

1. `README.md`
2. `docs/visao-geral.md`
3. `docs/arquitetura.md`
4. `docs/modulos.md`
5. `docs/fluxos-principais.md`
6. `docs/backend-api.md`

## O que cada modulo faz em uma frase

- `operacoes-goldcredit`: frontend principal no Lovable com edge functions de apoio
- `backend`: API de assinatura, autenticacao sensivel e documentos
- `app`: assinador local que usa certificados ICP-Brasil
- `banco-de-dados`: referencia do schema e evolucao SQL

## Pre-requisitos

- Node.js 18+
- Python 3.10+
- acesso ao projeto Supabase
- variaveis de ambiente do frontend e do backend
- certificado ICP-Brasil instalado para testar assinatura local

## Variaveis de ambiente mais importantes

### Frontend `operacoes-goldcredit`

- `VITE_SUPABASE_URL`
- `VITE_SUPABASE_PUBLISHABLE_KEY`
- `VITE_BACKEND_URL`
- `VITE_LOCAL_SIGNER_URL`

### Backend

- `SUPABASE_URL`
- `SUPABASE_SERVICE_KEY`
- `SUPABASE_DB_URL` opcional
- `JWT_SECRET`
- `FRONTEND_URL`
- `BACKEND_URL`

## Ordem recomendada para subir localmente

### 1. Frontend Lovable

```bash
cd operacoes-goldcredit
npm install
npm run dev
```

### 2. Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### 3. App local

```bash
cd app
pip install -r requirements.txt
python main.py
```

## Apoio com banco local

Existe um `docker-compose.yml` na raiz com PostgreSQL e backend. Ele ajuda em desenvolvimento local, mas o ambiente principal do sistema usa Supabase.

## Checklist de validacao rapida

Depois de subir o ambiente, valide:

1. frontend abre sem erro de variavel
2. backend responde em `/api/health`
3. app local responde em `/api/status`
4. login funciona
5. rotas protegidas carregam
6. criacao de solicitacao de assinatura funciona
7. listagem de certificados locais funciona

## Onde comecar ao pegar uma tarefa

### Se a tarefa for de tela, UX ou navegacao

Comece em `operacoes-goldcredit/src/pages` e `operacoes-goldcredit/src/components`.

### Se a tarefa for de integracao com assinatura

Olhe primeiro:

- `operacoes-goldcredit/src/lib/assinatura-api.ts`
- `backend/main.py`
- `backend/signature_service.py`
- `app/main.py`

### Se a tarefa for de dados ou acesso

Olhe primeiro:

- `operacoes-goldcredit/src/integrations/supabase`
- `operacoes-goldcredit/supabase/functions`
- `banco-de-dados`

## Dicas para onboarding interno

- nao descreva `operacoes-goldcredit` apenas como frontend
- sempre registre se a mudanca ficou no Lovable, no backend ou no app local
- quando criar edge function nova, documente objetivo, entrada, saida e dependencia externa
- quando criar rota nova no backend, atualize `docs/backend-api.md`

## Pendencias naturais da documentacao

Com o sistema evoluindo, ainda vale complementar depois:

- exemplos reais de payloads
- mapa de permissoes por papel
- inventario detalhado de edge functions
- runbook de incidentes e deploy
