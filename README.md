# Lavoura Inteligente — Rastreabilidade Agrícola e Conformidade EUDR

**Código da Disciplina**: IBM8936<br>
**Turma**: PC_ADS_26.2_8001_II<br>
**Case**: 6 — AgTech: "Lavoura Inteligente"<br>

## Integrantes

| Nome |
| -- |
| Joao Vitor Donda |
| Caique Rechuan |
| Joao Gabriel Meirelles |

## Sobre

A Lavoura Inteligente é uma plataforma de rastreabilidade agrícola. Ela consolida dados
de produtores, talhões, fontes ambientais (MapBiomas, DETER, Sentinel) e eventos de
recebimento, cruza os polígonos das áreas com essas fontes e mantém um status de risco
atualizado para cada talhão.

Quando um lote chega à cooperativa, a balança consulta o status já calculado e recebe,
em poucos segundos, **APROVADO**, **REVISÃO** ou **BLOQUEADO**, com motivo e evidências
versionadas. A regulamentação europeia contra desmatamento (EUDR) é usada como motivação
de negócio, não como aconselhamento jurídico.

O projeto é acadêmico e demonstra o uso integrado de serviços AWS com um limite de
**US$ 1.500 por mês**.

## Documentação principal

- [Documento de Visão](docs/Iniciacao/documento_de_visao.md)
- [Documento de Arquitetura](docs/Elaboracao/arquitetura.md)
- [Levantamento de Requisitos Funcionais](docs/Elaboracao/levreq.md)
- [Requisitos Suplementares](docs/Elaboracao/requisitos_suplementares.md)
- [Casos de Uso](docs/Elaboracao/casos_de_uso.md)
- [Modelo de Análise (Segurança)](docs/Elaboracao/modelo_analise_seguranca.md)

## Arquitetura resumida

| Necessidade | Serviço principal | Motivo |
| -- | -- | -- |
| Receber APIs | API Gateway | Entrada segura e gerenciada. |
| Executar lógica | Lambda | Serverless e orientado a eventos. |
| Status rápido | DynamoDB | Baixa latência na consulta da balança. |
| Arquivos e histórico | S3 | Data lake barato e escalável. |
| SQL histórico | Athena | Consulta direta no S3. |
| Eventos | EventBridge | Desacoplamento e agendamento. |
| Alertas | SNS | Notificações de mudança de status. |
| Geoespacial | PostgreSQL + PostGIS | Interseções, índices e relacionamentos espaciais. |
| Observabilidade | CloudWatch + CloudTrail | Métricas, logs e auditoria. |
| Interface | CloudFront + S3 | Dashboard com mapa e status. |

O sistema pré-processa os dados complexos: a análise espacial roda quando chega um novo
polígono ou dataset, e a balança apenas lê o status pronto no DynamoDB.

## Documentação local

```bash
pip install -r requirements.txt
mkdocs build --strict
mkdocs serve
```

O pipeline valida o build estrito em pull requests e publica o site após mudanças na
branch `main`.
