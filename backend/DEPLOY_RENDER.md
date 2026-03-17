# Deploy do backend no Render

O backend deste projeto sobe bem no Render como `Web Service` usando Docker.

## O que ja esta preparado

- O container inicia com `uvicorn` usando a porta de ambiente `PORT`.
- O backend expõe health check em `/api/health`.
- Existe um `render.yaml` na raiz do projeto para evitar configuracao manual repetitiva.

## Como publicar

1. Envie o repositorio para GitHub.
2. No Render, crie um novo `Blueprint` apontando para esse repositorio.
3. Confirme a criacao do servico `goldsign-backend`.
4. Preencha as variaveis obrigatorias pedidas no painel.

## Variaveis obrigatorias

- `SUPABASE_URL`
- `SUPABASE_SERVICE_KEY`
- `JWT_SECRET`

## Valores recomendados

- `SUPABASE_URL`: URL do projeto Supabase, por exemplo `https://xxxx.supabase.co`
- `SUPABASE_SERVICE_KEY`: chave `service_role` do Supabase
- `JWT_SECRET`: segredo longo e aleatorio

## Variaveis recomendadas apos o primeiro deploy

- `FRONTEND_URL`: URL publica do frontend ou do sistema pai que vai consumir o backend
- `BACKEND_URL`: URL publica final do backend no Render

## Observacoes importantes

- Se `FRONTEND_URL` ficar apontando para `localhost`, o CORS vai bloquear o frontend publicado.
- Se `BACKEND_URL` ficar incorreto, os links gerados pelo sistema podem sair com endereco errado.
- Como o frontend ainda nao sera publicado agora, essas duas variaveis podem ser ajustadas depois que o backend estiver online.
- O backend usa Supabase, entao o deploy so fica funcional depois de configurar as credenciais corretas.
