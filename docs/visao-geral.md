# Visao Geral

## O que e o GoldSign

O GoldSign e a solucao usada para operar documentos e assinaturas digitais dentro do contexto da Gold Credit. O sistema combina uma camada operacional para uso interno com um fluxo publico e seguro de assinatura digital.

Na pratica, o sistema cobre dois grupos de necessidade:

- operacao interna: cadastro, consulta, acompanhamento e gestao de dados de clientes, cedentes, carteira e documentos
- assinatura digital: envio de contratos, geracao de links, validacao do signatario e aplicacao da assinatura em padrao juridicamente aceito

## Problema que o sistema resolve

Antes de olhar tecnologia, e importante registrar o problema de negocio:

- centralizar a operacao em um unico ponto
- reduzir friccao na preparacao e assinatura de contratos
- permitir assinatura com certificado ICP-Brasil sem expor a chave privada do signatario
- manter trilha de auditoria e rastreabilidade de ponta a ponta

## Perfis de usuario identificados no sistema

Pelos fluxos e regras atuais do backend, os papeis principais sao:

- `adm`: administra a plataforma em nivel mais amplo
- `master`: conta principal da empresa no modelo SaaS
- `gestor`: opera clientes, documentos e solicitacoes
- `cliente`: visualiza e assina os documentos que lhe foram enviados

## Componentes do sistema

### `operacoes-goldcredit`

Frontend principal do projeto, desenvolvido no Lovable. E a interface de uso diario para o time interno e tambem inclui o fluxo publico de assinatura acessado por token.

### `backend`

API em FastAPI responsavel pelas regras de negocio mais sensiveis, principalmente autenticacao, documentos, solicitacoes de assinatura, validacao de certificado e auditoria.

### `app`

Aplicativo Python executado localmente na maquina do signatario. Ele acessa certificados A1/A3 instalados no ambiente e gera a assinatura local.

### `banco-de-dados`

Conjunto de scripts SQL, migrations e referencia do modelo de dados principal.

## Resultado esperado para quem entra no projeto

Uma pessoa nova deve conseguir responder rapidamente as perguntas abaixo:

- qual modulo mexe no que
- onde roda cada parte
- qual parte fala com Supabase
- qual parte fala com o app local
- onde entram as edge functions do Lovable
- qual o caminho dos dados durante uma assinatura

Os proximos documentos desta pasta foram organizados justamente para responder a essas perguntas.
