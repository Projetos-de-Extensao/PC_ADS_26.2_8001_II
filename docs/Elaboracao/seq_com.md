---
id: seq_com
title: Modelo de Design — Sequência e Comunicação
---

# Modelo de Design — Diagramas de Sequência e Comunicação (v1.0)

**Projeto**: Lavoura Inteligente — Rastreabilidade Agrícola e Conformidade EUDR<br>
**Fase**: Elaboração<br>
**Release**: 1 (AP2) — Django REST + PostgreSQL em Docker na EC2<br>
**Status**: Em revisão

## 1. Objetivo

Descrever os fluxos críticos da Release 1 (os objetos envolvidos e a ordem das
mensagens) e ligar cada requisito ao caso de uso, ao componente implementado e ao teste
ou evidência que o comprova.

## 2. Componentes participantes

| Componente | Implementação |
| -- | -- |
| Cliente | Balança, painel, Django Admin ou `curl` |
| Gunicorn | servidor WSGI no container `web` (porta 8000) |
| Router DRF | `conifg/urls.py` → `/api/produtores/`, `/api/fazendas/`, `/api/talhoes/`, `/api/lotes/`, `/api/lote-itens/` |
| `LoteViewSet` / `TalhaoViewSet` | `lavouraInteligente/views.py` |
| Serializers | `lavouraInteligente/serializers.py` |
| ORM / models | `lavouraInteligente/models.py` |
| PostgreSQL 16 | container `db`, volume `pgdata`, índice GIN `talhao_atributos_gin` |

## 3. Fluxo 1 — Recepção de lote na balança (transacional)

Endpoint: `POST /api/lotes/receber/`. Atende RF-LOT-01 a 04 e RN-08.

```mermaid
sequenceDiagram
    autonumber
    actor Op as Operador da balança
    participant G as Gunicorn (web)
    participant V as LoteViewSet.receber
    participant S as RecebimentoSerializer
    participant DB as PostgreSQL (db)

    Op->>G: POST /api/lotes/receber/ {codigo, peso_total_kg, itens[]}
    G->>V: requisição
    V->>S: is_valid()
    S->>DB: SELECT lote por código / talhões por id
    alt entrada inválida (código repetido, talhão inexistente)
        S-->>Op: 400 Bad Request
    else entrada válida
        V->>DB: BEGIN (transaction.atomic)
        V->>DB: INSERT Lote
        loop cada item
            V->>DB: SELECT Talhao ... FOR UPDATE
            V->>DB: INSERT LoteTalhao
        end
        alt soma dos pesos ≠ peso total ou talhão repetido
            V->>DB: ROLLBACK
            V-->>Op: 409 Conflict + motivo
        else regras de integridade OK
            V->>V: pior status (BLOQUEADO > REVISAO > APROVADO)
            V->>DB: UPDATE Lote (status, motivo)
            V->>DB: COMMIT
            V-->>Op: 201 Created {status, motivo, itens}
        end
    end
```

O `SELECT ... FOR UPDATE` trava os talhões durante a transação, para que uma revisão de
status simultânea não mude o talhão entre a leitura e a gravação do lote.

## 4. Fluxo 2 — Consulta de talhões por atributo JSON (documento)

Endpoint: `GET /api/talhoes/?atributos__<chave>=<valor>`. Atende RF-HIS-01 e o requisito
A3/A5 da AP2.

```mermaid
sequenceDiagram
    autonumber
    actor An as Analista
    participant V as TalhaoViewSet
    participant ORM as Django ORM
    participant DB as PostgreSQL

    An->>V: GET /api/talhoes/?atributos__contains={"fonte":"DETER"}
    V->>V: converte o valor com json.loads
    V->>ORM: Talhao.objects.filter(atributos__contains={...})
    ORM->>DB: SELECT ... WHERE atributos @> '{"fonte":"DETER"}'
    DB->>DB: Bitmap Index Scan on talhao_atributos_gin
    DB-->>V: linhas
    V-->>An: 200 OK [talhões]
```

Também são aceitos caminhos e comparadores (`?atributos__bioma=cerrado`,
`?atributos__ndvi__lt=0.5`). Uma chave inexistente devolve lista vazia.

## 5. Fluxo 3 — Deploy (Windows → GitHub → EC2)

Atende B5 da AP2 e RNF-MAN-01/03.

```mermaid
sequenceDiagram
    autonumber
    actor Dev as Desenvolvedor (Windows)
    participant GH as GitHub
    participant EC2 as EC2 (Amazon Linux 2023)
    participant C as Docker Compose
    participant W as container web
    participant D as container db

    Dev->>Dev: altera código e testa (docker compose up -d --build)
    Dev->>GH: git push
    GH-->>GH: CI "Deploy docs" (mkdocs build --strict)
    Dev->>EC2: ssh
    EC2->>GH: git pull (ou scripts/deploy_ec2.sh)
    EC2->>C: docker compose up -d --build
    C->>D: inicia postgres:16 (volume pgdata)
    D-->>C: healthcheck pg_isready OK
    C->>W: inicia web (depends_on: service_healthy)
    W->>W: manage.py bootstrap (collectstatic, migrate, superusuário, seed)
    W->>D: migrations
    W->>W: gunicorn :8000
    Dev->>W: GET http://IP:8000/api/ → 200
```

## 6. Diagrama de comunicação (visão estrutural)

```mermaid
flowchart LR
    Op([Operador / Analista / Admin]) -- "1: HTTP :8000" --> SG{{Security Group<br/>22 e 8000}}
    SG -- "2" --> W[container web<br/>Gunicorn + Django + WhiteNoise]
    W -- "3: SQL :5432<br/>rede interna do Compose" --> D[(container db<br/>PostgreSQL 16)]
    D -- "4" --> V[(volume pgdata)]
    W -. "5: .env (SECRET_KEY, POSTGRES_*)" .- E[[.env fora do Git]]
    B[scripts/backup_db.sh] -- "6: pg_dump" --> D
    B -- "7: cópia" --> S3[(S3)]
```

## 7. Matriz de rastreamento

| Requisito | Caso de uso | Componente | Teste / evidência |
| -- | -- | -- | -- |
| RF-CAD-01 (cadastro com relacionamentos) | UC-FUN-002 | `Produtor`, `Fazenda`, `Talhao`; `ProdutorViewSet`, `FazendaViewSet`, `TalhaoViewSet` | `RelacionalTests.test_crud_e_serializer_aninhado`, `test_relacionamentos` |
| RF-LOT-01 (lote com um ou mais talhões) | UC-FUN-006 | `Lote`, `LoteTalhao` (ManyToMany com peso) | `TransacaoTests.test_recebimento_grava_lote_e_itens` |
| RF-LOT-02 (status e motivo do lote) | UC-FUN-006 | `LoteViewSet.receber` | resposta 201 com `status` e `motivo`; print da API (README) |
| RF-LOT-03 / RN-08 (pior status) | UC-FUN-006 | `LoteViewSet.receber` | `TransacaoTests.test_lote_assume_pior_status_bloqueado` |
| RN-04 (talhão sem polígono não é APROVADO) | UC-FUN-005 | `LoteViewSet.receber` | revisão de código; seed com polígonos |
| A4 (transação com rollback) | UC-FUN-006 | `transaction.atomic` | `test_soma_de_pesos_divergente_faz_rollback`, `test_talhao_repetido_faz_rollback` |
| A3 (JSONB + GIN por migration) | UC-FUN-005, UC-FUN-009 | `Talhao.atributos`, migration `0001_initial` | `DocumentoJsonbTests.test_indice_gin_criado_pela_migration`; `EXPLAIN` com `Bitmap Index Scan` |
| A5 / RF-HIS-01 (filtro por campo JSON) | UC-FUN-009 | `TalhaoViewSet.get_queryset` | `test_filtro_por_chave_json`, `test_chave_json_inexistente_retorna_lista_vazia` |
| A6 / RF-IDN-03 (admin) | UC-FUN-001 | Django Admin, comando `bootstrap` | `AdminSeedTests.test_seed_idempotente_e_admin`; print do admin |
| A8 (seed) | — | comando `seed` | `test_seed_idempotente_e_admin` |
| RNF-SEG-05 (segredos fora do código) | CA-ARQ-007 | `settings.py` por variáveis, `.env` no `.gitignore`, `.env.example` | `git ls-files` sem `.env`; `.env` com permissão 600 |
| RNF-CON-03/04, RNF-OPS-04/05 (backup e restore) | CA-ARQ-008 | `scripts/backup_db.sh`, volume `pgdata` | restore testado em `restore_teste` (dimrbd.md, 5.2); prova de persistência `down`/`up` |
| RNF-MAN-01 (deploy automatizado) | CA-ARQ-009 | `scripts/deploy_ec2.sh`, `docker-compose.yml` | log do script na EC2 (README) |
| RNF-MAN-07 (docs publicáveis) | CA-ARQ-009 | `.github/workflows/mkdocs.yml` | CI "Deploy docs" verde |

## 8. Histórico e aprovação

| Versão | Data | Status | Descrição | Autor(es) |
| -- | -- | -- | -- | -- |
| 1.0 | 10/11/2026 | Em revisão | Fluxos de recepção transacional, consulta JSONB e deploy; matriz de rastreamento da Release 1. | Equipe do projeto |

| Papel aprovador | Nome | Data | Decisão |
| -- | -- | -- | -- |
| Arquiteto de Soluções | | | Pendente |
| Professor responsável | | | Pendente |
