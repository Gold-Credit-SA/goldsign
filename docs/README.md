# Documentacao do GoldSign

Esta pasta concentra a documentacao de referencia do sistema. A ideia e permitir que uma pessoa nova na empresa entenda rapidamente:

- qual problema o sistema resolve
- como os modulos se dividem
- quais fluxos de negocio existem
- como subir o ambiente local
- onde mexer quando precisar evoluir ou corrigir algo

## Ordem de leitura recomendada

1. [Visao Geral](./visao-geral.md)
2. [Arquitetura](./arquitetura.md)
3. [Modulos](./modulos.md)
4. [Fluxos Principais](./fluxos-principais.md)
5. [Backend API](./backend-api.md)
6. [Onboarding](./onboarding.md)

## Objetivo desta documentacao

Esta documentacao foi escrita para atender principalmente quatro perfis:

- novos desenvolvedores entrando no time
- pessoas de produto, operacao ou gestao que precisam entender o sistema em alto nivel
- mantenedores responsaveis por deploy, configuracao e suporte
- quem assumir partes especificas do frontend Lovable, backend de assinatura ou app local

## Convencoes

- `operacoes-goldcredit`: frontend principal desenvolvido no Lovable, com edge functions de apoio
- `backend`: API FastAPI responsavel pelas regras de assinatura digital e pelas rotas sensiveis
- `app`: aplicativo local que acessa certificados ICP-Brasil na maquina do signatario
- `banco-de-dados`: scripts SQL, migrations e referencia do banco

## Estado atual

O repositorio contem partes em estagios diferentes de maturidade. Por isso, esta pasta deve ser tratada como a documentacao central e a primeira fonte de consulta para onboarding. READMEs de modulo continuam uteis, mas podem ficar mais focados em execucao e manutencao local.
