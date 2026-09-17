# Lavoura Inteligente — Plataforma de Telemetria Agrícola

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

A Lavoura Inteligente recebe leituras de sensores agrícolas, avalia limiares de cada
cultura, publica alertas e consolida dados para painéis e relatórios. A arquitetura
separa a API administrativa, apoiada por PostgreSQL, do fluxo serverless de telemetria,
apoiado por DynamoDB, para que os picos de escrita não degradem o portal.

O projeto é acadêmico e demonstra o uso integrado de serviços AWS com um limite de
**US$ 1.500 por mês**.

## Documentação principal

- [Documento de Visão](docs/Iniciacao/documento_de_visao.md)
- [Levantamento de Requisitos Funcionais](docs/Elaboracao/levreq.md)
- [Requisitos Suplementares](docs/Elaboracao/requisitos_suplementares.md)
- [Casos de Uso](docs/Elaboracao/casos_de_uso.md)

## Arquitetura resumida

| Componente | Papel |
| -- | -- |
| API Gateway + Lambda | Autenticar, validar e persistir a telemetria. |
| DynamoDB | Séries temporais e projeções de consulta/limiares. |
| DynamoDB Streams + Lambda | Avaliação idempotente das regras e arquivamento explícito de eventos TTL. |
| SNS | Publicação dos alertas para os canais inscritos. |
| ALB + EC2 + RDS | Portal administrativo e dados transacionais. |
| S3 + CloudFront | Front-end estático, histórico e relatórios de safras. |
| CloudWatch | Logs, métricas, alarmes e evidências operacionais. |

Uma resposta de sucesso ao sensor só é emitida depois da persistência durável. O TTL
do DynamoDB remove itens; um consumidor do Streams realiza o arquivamento no S3 e trata
falhas de forma explícita.

## Documentação local

```bash
pip install -r requirements.txt
mkdocs build --strict
mkdocs serve
```

O pipeline valida o build estrito em pull requests e publica o site após mudanças na
branch `main`.
