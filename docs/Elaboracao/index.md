# Elaboração

> Objetivo: refinar os requisitos, resolver os riscos críticos e definir a arquitetura base.

## Resumo da fase

A Elaboração detalhou os requisitos funcionais, os casos de uso e a arquitetura-alvo
serverless. Para a Release 1 (AP2), a equipe validou a arquitetura base com um MVP em
**Django REST + PostgreSQL multimodelo** (relacional + JSONB com índice GIN) em
**Docker Compose na EC2**, dimensionou computação e banco e modelou os fluxos críticos.

## Artefatos

| Documento | Conteúdo |
| -- | -- |
| [Documento de Arquitetura](arquitetura.md) | Arquitetura-alvo AWS e a arquitetura implantada na Release 1. |
| [Requisitos Funcionais](levreq.md) | Perfis, requisitos funcionais e regras de negócio (RN-01 a RN-12). |
| [Casos de Uso Arquiteturais](cua.md) | Atores, diagrama, especificações, cenários arquiteturais e casos implementados na Release 1. |
| [Pacotes e Subsistemas](maps.md) | Pacotes de segurança da arquitetura-alvo e pacotes da aplicação Django (apps, API, dados, infraestrutura, segurança), com dependências e rastreabilidade. |
| [Dimensionamento de Computação (EC2)](dim_comp.md) | Tipo de instância justificado para web + db, classes de análise e memória de cálculo. |
| [Dimensionamento de Banco de Dados](dimrbd.md) | Volumetria, crescimento, armazenamento, backup e restauração; volume Docker x RDS. |
| [Sequência e Comunicação](seq_com.md) | Fluxos de recepção transacional, consulta JSONB e deploy; matriz de rastreamento. |

## Principais atividades

* Detalhar os requisitos mais importantes.
* Desenvolver uma arquitetura de software robusta.
* Criar protótipos ou provas de conceito.
* Planejar as próximas fases com mais precisão.
* Produto principal: arquitetura validada e plano de desenvolvimento para a Construção.
