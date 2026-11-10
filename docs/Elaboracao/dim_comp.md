---
id: dim_comp
title: Dimensionamento de Computação (EC2)
---

# Modelo de Análise — Dimensionamento de Computação (EC2) (v1.0)

**Projeto**: Lavoura Inteligente — Rastreabilidade Agrícola e Conformidade EUDR<br>
**Fase**: Elaboração<br>
**Release**: 1 (AP2) — EC2 + Docker Compose + PostgreSQL<br>
**Status**: Em revisão

## 1. Objetivo

Definir o tipo de instância EC2 que executa, na mesma máquina, os containers **web**
(Django + Gunicorn) e **db** (PostgreSQL 16) da Release 1, com base no cenário de
referência do [Documento de Requisitos Suplementares](../Iniciacao/rs.md) e em medições
feitas com a própria aplicação.

## 2. Carga de referência

| Item | Valor | Origem |
| -- | -- | -- |
| Produtores / talhões | 3.000 / 25.000 | rs.md, seção 2 |
| Consultas na balança | até 5.000 por dia; pico de 20 req/s por 30 min | RNF-CAP-02 |
| Tempo de resposta da balança | p95 < 500 ms | RNF-PER-01 |
| Usuários simultâneos no admin/painel | até 10 | estimativa da equipe |
| Crescimento | 2x talhões sem mudança estrutural | RNF-CAP-01 |

## 3. Classes de análise da Release 1

As classes abaixo são as que consomem CPU e memória em cada requisição. Elas
correspondem aos models, serializers e views do app Django `lavouraInteligente`.

```plantuml
@startuml dim_comp_classes
skinparam classAttributeIconSize 0
hide empty members

package "Fronteira (API DRF)" {
  class LoteViewSet <<boundary>> {
    +receber(request)
  }
  class TalhaoViewSet <<boundary>> {
    +get_queryset()
  }
  class "Produtor/FazendaViewSet" as CadViewSet <<boundary>>
}

package "Controle (regras)" {
  class RecebimentoSerializer <<control>> {
    +validate_codigo()
  }
  class "transaction.atomic" as Tx <<control>>
}

package "Entidade (PostgreSQL)" {
  class Produtor <<entity>>
  class Fazenda <<entity>>
  class Talhao <<entity>> {
    atributos : JSONB (GIN)
    poligono : JSONB
    status
  }
  class Lote <<entity>> {
    status
    motivo
  }
  class LoteTalhao <<entity>> {
    peso_kg
  }
}

LoteViewSet --> RecebimentoSerializer : valida entrada
LoteViewSet --> Tx : grava Lote + itens
Tx --> Lote
Tx --> LoteTalhao
TalhaoViewSet --> Talhao : atributos @> {...}
CadViewSet --> Produtor
CadViewSet --> Fazenda
Produtor "1" -- "*" Fazenda
Fazenda "1" -- "*" Talhao
Lote "1" -- "*" LoteTalhao
Talhao "1" -- "*" LoteTalhao
@enduml
```

| Classe | Operação crítica | Custo dominante |
| -- | -- | -- |
| `LoteViewSet.receber` | 1 INSERT de lote + N (SELECT FOR UPDATE + INSERT) + 1 UPDATE numa transação | I/O do Postgres (commit) |
| `TalhaoViewSet` | consulta por chave JSON com índice GIN | CPU do Postgres + serialização JSON |
| `ProdutorViewSet` | serializer aninhado (produtor → fazendas → talhões) com `prefetch_related` | CPU do Gunicorn (serialização) |
| `bootstrap` (deploy) | `collectstatic` + `migrate` + seed | executa só na subida do container |

## 4. Medições com a aplicação

Ambiente de teste da equipe (container local, mesma imagem e mesmo Compose da EC2), com
o seed carregado:

| Medida | Resultado |
| -- | -- |
| Memória do container `web` (Gunicorn com 3 workers) | ~150 MiB |
| Memória do container `db` (PostgreSQL 16 ocioso) | ~52 MiB |
| `GET /api/talhoes/` — 20 requisições sequenciais | p50 = 11 ms; p95 = 49 ms |
| Consulta `atributos @> '{"fonte": "DETER"}'` | plano usa `Bitmap Index Scan on talhao_atributos_gin` |

As medições de tempo foram feitas fora da EC2 e servem como ordem de grandeza. O teste
de carga de 20 req/s (RNF-CAP-02) deve ser repetido na instância escolhida e registrado
nas evidências do README.

## 5. Memória de cálculo

| Componente | Memória estimada | Base |
| -- | -- | -- |
| Amazon Linux 2023 + Docker Engine | ~400 MiB | sistema operacional e daemon |
| `web`: Gunicorn, 3 workers | ~150 MiB (medido) → até 300 MiB sob carga | ~50–100 MiB por worker |
| `db`: PostgreSQL 16 | 52 MiB ocioso → ~400 MiB com `shared_buffers` 128 MiB, cache e 20 conexões | padrão da imagem oficial |
| Folga para `docker compose build` (pip install) | ~300 MiB | pico só durante o deploy |
| **Total no pico** | **~1,4 GiB** | |

**Throughput**: cada requisição da balança gasta ~10–50 ms. Com 3 workers síncronos, a
capacidade teórica é de 60 a 300 req/s, acima do pico de 20 req/s exigido. O gargalo
esperado é o disco do banco nos commits, e não a CPU.

**Workers**: a regra usual é `2 × vCPU + 1`. Na t3.small isso daria 5 workers, mas a
equipe fixou 3 (`--workers 3` no `Dockerfile`) para deixar memória ao Postgres.

## 6. Escolha da instância

| Tipo | vCPU | Memória | Preço on-demand* | Avaliação |
| -- | -- | -- | -- | -- |
| t3.micro | 2 | 1 GiB | ~US$ 7,59/mês | Funciona para demonstração, mas o pico de ~1,4 GiB exige swap e o build fica lento. |
| **t3.small** | **2** | **2 GiB** | **~US$ 15,18/mês** | **Escolhida**: atende ao pico com folga de ~600 MiB e créditos de CPU suficientes para a balança. |
| t3.medium | 2 | 4 GiB | ~US$ 30,37/mês | Indicada se o teste de carga mostrar falta de memória ou para 2x talhões com muitos usuários. |

\* Região us-east-2 (Ohio), Linux, 730 h/mês. São valores de referência que devem ser
conferidos no AWS Pricing Calculator na data da entrega (RNF-CUS-04).

**Decisão**: **t3.small**, com volume EBS gp3 de 30 GB (ver
[Dimensionamento de Banco de Dados](dimrbd.md)). Se a equipe usar uma t3.micro do Free
Tier na demonstração, deve criar 1 GiB de swap antes do primeiro build.

## 7. Escalabilidade e limites da Release 1

- **Vertical**: trocar o tipo da instância (t3.small → t3.medium) exige parar e iniciar a
  instância. Com Elastic IP o endereço da API não muda.
- **Horizontal**: o Compose roda numa única máquina. Escalar o `web` em várias instâncias
  exige tirar o banco da EC2 (RDS) e colocar um balanceador, o que é a evolução prevista
  em [Estratégias de Deploy](../Transicao/ativ_deploy.md).
- **Ponto único de falha**: web e db na mesma instância. A disponibilidade alvo da Release 1
  é menor que a da arquitetura final (ver rs.md, seção 13).

## 8. Histórico e aprovação

| Versão | Data | Status | Descrição | Autor(es) |
| -- | -- | -- | -- | -- |
| 1.0 | 10/11/2026 | Em revisão | Dimensionamento da EC2 para web + db em Docker Compose (Release 1). | Equipe do projeto |

| Papel aprovador | Nome | Data | Decisão |
| -- | -- | -- | -- |
| Arquiteto de Soluções | | | Pendente |
| Professor responsável | | | Pendente |
