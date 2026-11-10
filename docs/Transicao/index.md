# Transição

> Objetivo: entregar o sistema ao ambiente de produção e aos usuários finais.

## Resumo da fase

A Release 1 sai do Elastic Beanstalk com SQLite (AP1) e passa a rodar em **EC2 com Docker
Compose** (containers `web` e `db`) e **PostgreSQL** com volume persistente. O deploy é
feito pelo fluxo Windows → GitHub → EC2, com o script `scripts/deploy_ec2.sh`.

## Artefatos

| Documento | Conteúdo |
| -- | -- |
| [Estratégias de Deploy (Atividades)](ativ_deploy.md) | Estratégias avaliadas, decisão, diagrama de atividades, tempo, custo e plano de rollback. |
| [Deploy EC2 + Docker (PostgreSQL)](../Construcao/deploy_ec2_postgres.md) | Roteiro passo a passo do deploy. |

## Principais atividades

* Realizar testes finais de aceitação.
* Treinar os usuários.
* Corrigir defeitos encontrados após a entrega.
* Preparar o ambiente de produção.
* Produto principal: sistema funcionando no ambiente do cliente com usuários treinados.
