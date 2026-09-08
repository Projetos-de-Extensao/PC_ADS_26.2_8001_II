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

A Lavoura Inteligente é uma plataforma de análise de dados agrícolas implantada na
nuvem AWS. Sensores IoT distribuídos por lavouras de grande extensão enviam, a cada
minuto, leituras de umidade do solo, acidez, temperatura e clima. A plataforma recebe
essa telemetria, avalia os limiares críticos de cada cultura e emite alertas de
irrigação aos produtores, além de consolidar os dados para os painéis consultados
pelos agrônomos de campo.

O sistema atual usa um banco de dados relacional que não suporta a alta concorrência
de escritas simultâneas de séries temporais. O resultado é lentidão extrema no banco,
risco de perda de leituras nos picos de ingestão e atrasos de até horas na emissão dos
alertas — justamente os alertas que precisam chegar em tempo real. O projeto reprojeta
essa arquitetura sobre serviços gerenciados e escaláveis, substituindo o banco
relacional por um modelo NoSQL de escrita distribuída.

O projeto é acadêmico e tem como objetivo demonstrar, em uma arquitetura funcional, o
uso integrado dos serviços de nuvem estudados na disciplina, respeitando o orçamento de
até **US$ 1.500,00/mês** definido para a infraestrutura.

A documentação completa do projeto está em [docs/](docs/), com destaque para o
[Documento de Visão](docs/Iniciacao/documento_de_visao.md) e o
[Levantamento de Requisitos](docs/Elaboracao/levreq.md).

### Arquitetura

| Serviço AWS | Papel |
| -- | -- |
| Amazon API Gateway | Endpoint HTTPS de entrada da telemetria enviada pelos sensores |
| AWS Lambda (ingestão) | Validação e sanitização dos payloads antes da gravação |
| Amazon DynamoDB | Persistência dos dados brutos de telemetria, particionados por sensor e ordenados por tempo |
| Amazon DynamoDB Streams + AWS Lambda | Avaliação dos limiares críticos e disparo dos alertas de irrigação |
| Amazon SNS | Entrega dos alertas aos produtores |
| Amazon S3 | Arquivos históricos e consolidados de safras passadas |
| Amazon S3 + Amazon CloudFront | Frontend dos painéis, distribuído com HTTPS |
| Amazon CloudWatch | Logs, métricas de ingestão e alarme de falha das funções Lambda |

Decisões que sustentam a escolha:

- **DynamoDB no lugar do relacional**: a escrita é distribuída pela chave de partição
  (`sensor_id`) com ordenação por `timestamp`, o que elimina a contenção de escrita das
  séries temporais e permite escalar horizontalmente.
- **Processamento orientado a eventos**: os alertas nascem do próprio stream de escrita
  do DynamoDB, reduzindo a latência de horas para segundos.
- **Serverless**: não há servidores a provisionar e o custo acompanha o volume real de
  telemetria, o que ajuda a manter o gasto dentro do orçamento.
- **TTL e camada fria**: os registros brutos expiram no DynamoDB após a janela de
  consulta quente e o histórico permanece no S3, com custo por GB muito menor.

## Instalação

**Linguagens**: Python<br>
**Infraestrutura como código**: AWS CDK em Python<br>
**Tecnologias**: AWS, GitHub, Visual Studio Code<br>
**Documentação**: MkDocs Material<br>

Pré-requisitos para executar o projeto:

- conta AWS com credenciais configuradas localmente;
- Python e AWS CDK instalados;
- limiares de irrigação por cultura definidos para a carga inicial das regras de alerta.

Etapas de implantação:

1. provisionar a infraestrutura com `cdk deploy`;
2. carregar as regras de alerta e o cadastro dos sensores;
3. publicar o frontend dos painéis no bucket S3;
4. validar a ingestão com uma carga simulada de telemetria.

Para consultar a documentação localmente:

```bash
pip install -r requirements.txt
mkdocs serve
```

