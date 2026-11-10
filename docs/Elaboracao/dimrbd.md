---
id: dimrbd
title: Dimensionamento de Banco de Dados
---

# Modelo de Análise — Dimensionamento de Banco de Dados (v1.0)

**Projeto**: Lavoura Inteligente — Rastreabilidade Agrícola e Conformidade EUDR<br>
**Fase**: Elaboração<br>
**Release**: 1 (AP2) — PostgreSQL 16 em container, volume Docker `pgdata`<br>
**Status**: Em revisão

## 1. Objetivo

Estimar volume, crescimento, armazenamento e a estratégia de backup e restauração do
banco PostgreSQL da Release 1. O documento também compara a opção adotada (volume
Docker na EC2) com o Amazon RDS.

## 2. Modelo de dados (multimodelo no mesmo PostgreSQL)

| Tabela | Paradigma | Conteúdo |
| -- | -- | -- |
| `Produtor` | relacional | nome, CPF/CNPJ (único), município, UF |
| `Fazenda` | relacional (FK → Produtor) | nome, código CAR, área |
| `Talhao` | relacional (FK → Fazenda) + **documento** | código, cultura, área, status; `poligono` (GeoJSON em JSONB) e `atributos` (JSONB com **índice GIN**) |
| `Lote` | relacional | código, data de recebimento, peso total, status e motivo |
| `LoteTalhao` | relacional (FK → Lote e FK → Talhao) | tabela associativa do **ManyToMany** com o peso de cada talhão de origem |

O JSONB guarda os dados que variam por fonte e por talhão (bioma, NDVI, alertas DETER,
certificações) sem exigir uma migration para cada novo atributo. Os dados que precisam
de integridade (cadastro, lote e pesos) ficam nas colunas relacionais com ACID.

## 3. Volumetria e memória de cálculo

Premissas: cenário de referência do [rs.md](../Iniciacao/rs.md) (3.000 produtores e 25.000
talhões), em média 2 fazendas por produtor, polígonos de ~200 vértices (cerca de 8 KB de
GeoJSON) e 1 KB de atributos por talhão.

| Tabela | Linhas no ano 1 | Tamanho médio da linha | Volume |
| -- | -- | -- | -- |
| Produtor | 3.000 | 0,3 KB | ~1 MB |
| Fazenda | 6.000 | 0,3 KB | ~2 MB |
| Talhao | 25.000 | 9,2 KB (0,2 colunas + 8 polígono + 1 atributos) | ~230 MB |
| Índice GIN de `atributos` | — | ~50% do JSON indexado | ~13 MB |
| Lote | ~313.500 por ano¹ | 0,4 KB | ~125 MB |
| LoteTalhao | ~470.000 por ano (1,5 itens por lote) | 0,12 KB | ~56 MB |
| Índices B-tree (PK, FK, únicos) | — | ~30% das tabelas de lote | ~55 MB |
| **Total no ano 1** | | | **~0,5 GB** |

¹ Colheita: 2.000 lotes/dia × 120 dias = 240.000. Restante do ano: 300 lotes/dia × 245
dias = 73.500.

### 3.1. Crescimento em 3 anos

| Ano | Talhões | Lotes acumulados | Volume de dados | Com WAL e folga (× 1,5) |
| -- | -- | -- | -- | -- |
| 1 | 25.000 | 313.500 | ~0,5 GB | ~0,75 GB |
| 2 | 37.500 | 627.000 | ~0,85 GB | ~1,3 GB |
| 3 | 50.000 (2x, RNF-CAP-01) | 940.500 | ~1,3 GB | ~2 GB |

O banco operacional cabe com folga em um volume pequeno. O que cresce de verdade são os
arquivos (KML originais, ortomosaicos de drone). Eles **não** ficam no PostgreSQL: na
arquitetura final vão para o S3 (RNF-CUS-03 e RNF-CUS-06).

## 4. Armazenamento na EC2

| Uso do disco EBS (gp3) | Espaço |
| -- | -- |
| Amazon Linux 2023 | ~8 GB |
| Imagens Docker (python:3.12-slim + app, postgres:16) | ~1,5 GB |
| Volume `pgdata` no ano 3 | ~2 GB |
| Backups locais (7 dumps diários compactados) | ~1 GB |
| Folga para logs, build e atualizações | ~10 GB |
| **Volume escolhido** | **30 GB gp3** (3.000 IOPS e 125 MB/s de base) |

Custo de referência do EBS gp3 (us-east-2): US$ 0,08/GB-mês × 30 GB = **~US$ 2,40/mês**.

## 5. Backup e restauração

### 5.1. Estratégia da Release 1

| Item | Definição |
| -- | -- |
| Ferramenta | `pg_dump` lógico, executado por `scripts/backup_db.sh` |
| Frequência | diária, agendada no `cron` da EC2 (ex.: `0 3 * * * bash ~/PC_ADS_26.2_8001_II/scripts/backup_db.sh`) |
| Retenção | 7 diários na EC2 e cópia para o S3 com 7 diários + 4 semanais |
| Tamanho do dump | ~25–35% do banco após gzip (~150 MB no ano 1) |
| Custo no S3 | ~11 dumps × 0,15 GB × US$ 0,023 = **< US$ 0,05/mês** |
| RPO | **24 h** (intervalo entre dumps) |
| RTO | **< 30 min**: subir a stack, restaurar o dump e conferir as contagens |

### 5.2. Procedimento de restauração (testado)

```bash
cd ~/PC_ADS_26.2_8001_II/src
docker compose up -d db
gunzip -c backups/<arquivo>.sql.gz | docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
docker compose up -d web
```

Teste da equipe: o dump do banco com o seed foi restaurado num banco novo
(`restore_teste`), com as mesmas contagens (4 talhões, 1 lote) e o índice
`talhao_atributos_gin` recriado.

### 5.3. Lacuna em relação à meta final

O RNF-CON-03 pede RPO inferior a 15 min, e o `pg_dump` diário da Release 1 entrega 24 h.
Para cumprir a meta é preciso arquivamento contínuo de WAL (por exemplo, com pgBackRest)
ou o PITR automático do RDS. Essa é uma das razões da evolução para RDS descrita na
seção 6.

## 6. Volume Docker na EC2 x Amazon RDS

| Critério | Volume Docker na EC2 (Release 1) | Amazon RDS for PostgreSQL |
| -- | -- | -- |
| Custo mensal* | incluso na EC2 + EBS (~US$ 2,40 de disco) | db.t4g.micro Single-AZ ~US$ 11,68 + 20 GB gp3 ~US$ 2,30; Multi-AZ ~2x |
| Backup | manual (`pg_dump` + cron + S3) | automático, com PITR de até 35 dias |
| RPO / RTO | 24 h / < 30 min | ~5 min (PITR) / minutos (Multi-AZ com failover) |
| Alta disponibilidade | não (mesma instância do web) | Multi-AZ opcional |
| Atualização e patches | responsabilidade da equipe (`image: postgres:16`) | gerenciados pela AWS |
| Exposição de rede | sem porta publicada; só a rede interna do Compose | sub-rede privada + Security Group só do web |
| Extensões (PostGIS, pgvector) | qualquer imagem/extensão | lista suportada pelo RDS (inclui PostGIS e pgvector) |
| Adequação | MVP, demonstração e custo mínimo | produção com SLA de 99,9% e RPO de 15 min |

\* Valores de referência on-demand em us-east-2; conferir no AWS Pricing Calculator.

**Decisão**: a Release 1 usa o **volume Docker** pelo custo e pela simplicidade exigidos
na AP2. A migração para o **RDS** é o primeiro passo da evolução, porque resolve ao mesmo
tempo o RPO (RNF-CON-03), a disponibilidade (RNF-CON-01) e permite escalar o web
horizontalmente.

## 7. Configuração e segurança do banco

- Credenciais apenas no `.env` (fora do Git); o repositório tem só o `.env.example`.
- O serviço `db` não publica a porta 5432, e o Security Group não libera essa porta.
- O `healthcheck` com `pg_isready` impede o web de rodar o `migrate` antes do banco estar pronto.
- O volume nomeado `pgdata` sobrevive a `docker compose down`. **`docker compose down -v`
  apaga os dados**, por isso não deve ser usado na EC2.

## 8. Histórico e aprovação

| Versão | Data | Status | Descrição | Autor(es) |
| -- | -- | -- | -- | -- |
| 1.0 | 10/11/2026 | Em revisão | Volumetria, armazenamento, backup/restore e comparação volume Docker x RDS (Release 1). | Equipe do projeto |

| Papel aprovador | Nome | Data | Decisão |
| -- | -- | -- | -- |
| Arquiteto de Soluções | | | Pendente |
| Professor responsável | | | Pendente |
