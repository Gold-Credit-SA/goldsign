# Fluxos Principais

## Objetivo

Documentar os fluxos de negocio que uma pessoa nova precisa entender antes de alterar o sistema.

## 1. Acesso interno ao sistema

### Objetivo

Permitir que usuarios internos acessem a plataforma conforme seu papel.

### Passos

1. O usuario acessa o frontend em `operacoes-goldcredit`.
2. O frontend autentica o usuario.
3. O perfil retornado define o que pode ser acessado.
4. Rotas protegidas passam a ser liberadas conforme o papel.

### Modulos envolvidos

- `operacoes-goldcredit`
- `backend`
- Supabase

## 2. Gestao de clientes e operacao interna

### Objetivo

Permitir que o time interno cadastre, consulte e acompanhe clientes, cedentes e dados operacionais.

### Passos

1. O usuario acessa telas como `/clientes`, `/consulta` e `/consultas`.
2. O frontend consome Supabase e edge functions.
3. Os dados retornam para exibicao, filtro e acompanhamento.

### Modulos envolvidos

- `operacoes-goldcredit`
- Supabase
- edge functions do proprio modulo

## 3. Criacao de solicitacao de assinatura

### Objetivo

Transformar um ou mais documentos em uma operacao assinavel.

### Passos

1. O usuario interno acessa a area de assinatura digital.
2. O frontend monta um `multipart/form-data` com os arquivos e metadados de assinatura.
3. O backend recebe os PDFs, grava metadados e cria as solicitacoes.
4. O backend gera tokens e links publicos.
5. O frontend exibe ou distribui os links para os signatarios.

### Regras importantes

- a operacao pode conter multiplos documentos
- existe suporte a papeis distintos de assinatura
- ha casos com assinatura da Gold Credit e responsavel solidario
- a expiracao do link e controlada no backend

### Modulos envolvidos

- `operacoes-goldcredit`
- `backend`
- `banco-de-dados`

## 4. Assinatura publica por token

### Objetivo

Permitir que um signatario assine sem precisar acessar a area autenticada do sistema.

### Passos

1. O signatario abre um link do tipo `/assinar/:token`.
2. O frontend consulta o backend para obter os dados da solicitacao.
3. O PDF e exibido para leitura.
4. O frontend verifica se o assinador local esta ativo.
5. O frontend lista os certificados disponiveis na maquina.
6. O usuario escolhe um certificado e confirma a assinatura.
7. O app local assina o hash localmente.
8. O frontend envia a assinatura CMS ao backend.
9. O backend valida, aplica a assinatura ao PDF e conclui a solicitacao.

### Regra critica

A chave privada nunca deve sair da maquina do signatario.

### Modulos envolvidos

- `operacoes-goldcredit`
- `app`
- `backend`
- `banco-de-dados`

## 5. Assinatura em lote por operacao

### Objetivo

Permitir que um mesmo signatario acompanhe varios documentos relacionados por um mesmo `bundle_token`.

### Passos

1. O usuario acessa `/assinar-operacao/:token`.
2. O frontend busca os documentos da operacao.
3. O sistema exibe progresso de itens assinados e pendentes.
4. Cada documento continua obedecendo as validacoes do fluxo individual.

### Modulos envolvidos

- `operacoes-goldcredit`
- `backend`

## 6. Auditoria e rastreabilidade

### Objetivo

Garantir que o ciclo do documento possa ser reconstituido depois.

### Eventos esperados

- criacao de documento
- criacao de solicitacao
- visualizacao pelo signatario
- preparacao da assinatura
- assinatura concluida
- expiracao ou bloqueio quando aplicavel

### Modulos envolvidos

- `backend`
- `banco-de-dados`

## 7. Administracao e configuracoes

### Objetivo

Permitir administracao de empresas, gestores, usuarios e configuracoes operacionais.

### Pontos de entrada identificados

- rotas `/admin` no frontend
- endpoints administrativos no backend
- edge functions ligadas a configuracao e bootstrap

### Modulos envolvidos

- `operacoes-goldcredit`
- `backend`
- Supabase
