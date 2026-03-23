# Backend API

## Objetivo

Organizar a API do backend por dominio funcional para facilitar manutencao e onboarding. Este documento nao substitui a leitura do codigo, mas serve como mapa inicial.

## Base

- stack: FastAPI
- arquivo principal: `backend/main.py`
- health check: `GET /api/health`

## 1. Setup inicial

- `POST /api/setup/primeiro-admin`

Uso:

- cria o primeiro administrador do sistema
- deve ser usado apenas em ambiente sem admin cadastrado

## 2. Autenticacao e perfil

- `POST /api/auth/login`
- `POST /api/auth/registro-master`
- `GET /api/auth/me`
- `PUT /api/auth/me`
- `POST /api/auth/certificado/desafio`
- `POST /api/auth/certificado/verificar`

Uso:

- login tradicional
- registro da conta principal
- leitura e atualizacao do perfil
- autenticacao por certificado em fluxos suportados

## 3. Administracao

### Empresas

- `POST /api/adm/empresas`
- `GET /api/adm/empresas`

### Gestores

- `POST /api/adm/gestores`
- `GET /api/adm/gestores`
- `PUT /api/adm/gestores/{gestor_id}`
- `DELETE /api/adm/gestores/{gestor_id}`

Uso:

- cadastrar e manter estrutura administrativa

## 4. Gestao de clientes

- `POST /api/gestor/clientes`
- `GET /api/gestor/clientes`
- `PUT /api/gestor/clientes/{cliente_id}`
- `DELETE /api/gestor/clientes/{cliente_id}`

### Socios vinculados ao cliente

- `GET /api/gestor/clientes/{cliente_id}/socios`
- `POST /api/gestor/clientes/{cliente_id}/socios`
- `PUT /api/gestor/clientes/{cliente_id}/socios/{socio_id}`
- `DELETE /api/gestor/clientes/{cliente_id}/socios/{socio_id}`

Uso:

- manter clientes e documentos permitidos para assinatura

## 5. Documentos

- `POST /api/documentos/upload`
- `GET /api/documentos`
- `GET /api/documentos/{documento_id}`
- `DELETE /api/documentos/{documento_id}`
- `GET /api/documentos/{documento_id}/download`
- `GET /api/documentos/{documento_id}/download-assinado`
- `POST /api/documentos/{documento_id}/solicitar-assinatura`
- `GET /api/documentos/{documento_id}/solicitacoes`

Uso:

- registrar documentos
- disponibilizar download
- acompanhar status e solicitacoes vinculadas

## 6. Solicitacoes para cliente autenticado

- `GET /api/cliente/solicitacoes`

Uso:

- listar solicitacoes relacionadas ao cliente logado

## 7. Fluxo publico de assinatura

### Criacao e listagem

- `POST /api/assinatura/criar`
- `GET /api/assinatura/criar`
- `GET /api/assinatura/listar`

### Operacao e token publico

- `GET /api/assinatura/operacao/{bundle_token}`
- `GET /api/assinatura/{token}`
- `GET /api/assinatura/{token}/pdf`
- `GET /api/assinatura/{token}/download-assinado`

### Validacao e assinatura

- `POST /api/assinatura/{token}/validar-certificado`
- `POST /api/assinatura/{token}/preparar`
- `POST /api/assinatura/submeter`

Uso:

- criar operacoes assinaveis
- consultar documentos publicos por token
- validar o certificado do signatario
- preparar o PDF para assinatura externa
- receber o CMS/PKCS#7 e consolidar o PDF assinado

## 8. Regras sensiveis observadas

- links de assinatura expiram
- ordem de assinatura pode bloquear o fluxo
- o backend controla preparacao concorrente por documento
- o certificado precisa bater com os documentos permitidos para a solicitacao
- eventos de auditoria sao registrados ao longo do processo

## 9. Recomendacoes de evolucao desta documentacao

Quando a API estabilizar mais, vale complementar este arquivo com:

- exemplos de request/response por rota
- codigos de erro esperados
- tabela de permissoes por papel
- diagramas de sequencia para o fluxo de assinatura
