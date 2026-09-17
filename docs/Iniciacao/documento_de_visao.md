---
id: documento_de_visao
title: Documento de Visão
---

# Documento de Visão (v1.1)

**Projeto**: Lavoura Inteligente — Plataforma de Telemetria Agrícola<br>
**Case**: 6 — AgTech<br>
**Turma**: PC_ADS_26.2_8001_II<br>
**Fase**: Iniciação<br>
**Status**: Em revisão

## 1. Introdução

Este documento apresenta o problema de negócio, os usuários, o escopo e as metas de
qualidade da plataforma Lavoura Inteligente. Os detalhes funcionais e os critérios
mensuráveis são mantidos, respectivamente, no Levantamento de Requisitos e no Documento
de Requisitos Suplementares.

### 1.1. Propósito

Definir uma visão comum para uma plataforma capaz de receber telemetria agrícola em
escala, transformar leituras críticas em alertas e oferecer dados atuais e históricos
sem que o pico de ingestão prejudique o portal administrativo.

### 1.2. Escopo

Estão no escopo:

1. cadastro de fazendas, talhões, culturas, sensores, usuários e limiares;
2. autenticação e autorização de usuários e sensores;
3. recepção, validação e persistência de telemetria;
4. avaliação de limiares e publicação de alertas;
5. painel de estado e histórico por talhão;
6. encerramento e relatórios de safra;
7. arquivamento da telemetria expirada;
8. infraestrutura AWS, segurança, observabilidade, backup, recuperação e CI/CD.

Estão fora do escopo desta fase a fabricação e homologação dos sensores, o
acionamento automático de pivôs de irrigação e a previsão por aprendizado de máquina.

### 1.3. Glossário

- **Leitura aceita**: leitura válida cuja persistência durável foi confirmada antes da
  resposta de sucesso ao sensor.
- **Alerta publicado**: alerta entregue com sucesso pelo motor de regras ao tópico SNS.
- **Alerta entregue**: alerta cuja entrega foi confirmada pelo canal, quando o canal
  oferece essa confirmação.
- **Talhão**: menor unidade de manejo da lavoura à qual os sensores são associados.
- **DLQ/destino de falha**: armazenamento durável de eventos que excederam a política de
  tentativas e precisam de inspeção ou replay.
- **SLA/SLO/SLI**: acordo, objetivo e indicador de nível de serviço.
- **RPO/RTO/MTTR**: perda máxima de dados, tempo de recuperação e tempo médio de reparo.
- **IaC**: infraestrutura como código.

### 1.4. Referências

- AWS Well-Architected Framework.
- Lei Geral de Proteção de Dados (Lei nº 13.709/2018).
- Documentação oficial de Amazon DynamoDB, AWS Lambda, Amazon VPC e Amazon S3.
- Plano de Ensino e roteiro do Case 6 — AgTech.

## 2. Posicionamento

### 2.1. Problema e oportunidade

O sistema atual concentra dados transacionais e séries temporais em um banco relacional.
Sob concorrência elevada, essa arquitetura produz contenção, risco de perda de leitura,
painéis desatualizados e alertas atrasados. A oportunidade é aproveitar os sensores já
instalados e converter a telemetria em decisão de manejo com uma arquitetura elástica.

### 2.2. Posicionamento do produto

Para empresas do agronegócio com lavouras conectadas, a **Lavoura Inteligente** é uma
plataforma de telemetria e alertas que persiste leituras em escala, publica alertas
críticos em menos de 60 segundos e oferece visão consolidada por talhão. Diferentemente
da solução atual, a ingestão serverless e o armazenamento de séries temporais permanecem
isolados da API administrativa.

## 3. Stakeholders e usuários

| Perfil | Necessidade primária | Resultado esperado |
| -- | -- | -- |
| Agrônomo | Acompanhar solo, clima e alertas por talhão. | Decidir o manejo com dados recentes. |
| Produtor rural | Receber alertas relevantes. | Agir antes de uma condição crítica causar perdas. |
| Gestor agrícola | Comparar fazendas e safras. | Obter relatórios consolidados sem afetar a ingestão. |
| Administrador | Manter cadastros, usuários, sensores e limiares. | Dados íntegros e acessos controlados. |
| Sensor IoT | Enviar leitura autenticada e identificável. | Confirmação inequívoca de aceitação ou rejeição. |
| Operação/DevOps | Implantar, observar e recuperar o serviço. | Operação rastreável dentro dos SLOs e do orçamento. |
| Segurança/CISO | Proteger dados pessoais e comerciais. | Menor privilégio, criptografia e auditoria. |
| Diretoria/CFO | Controlar o gasto. | Custo total inferior a US$ 1.500 por mês. |
| Corpo docente | Avaliar a solução. | Decisões justificadas e evidências reproduzíveis. |

## 4. Visão da solução

### 4.1. Fluxo administrativo

O CloudFront distribui os arquivos estáticos do front-end hospedados no S3. O tráfego
dinâmico segue por HTTPS ao Application Load Balancer em sub-redes públicas. A aplicação
Django REST Framework roda em pelo menos duas instâncias EC2 privadas, distribuídas em
duas Zonas de Disponibilidade, e acessa o RDS PostgreSQL Multi-AZ em sub-redes privadas.

### 4.2. Fluxo de telemetria

O API Gateway, como serviço regional gerenciado, recebe requisições HTTPS autenticadas e
invoca a Lambda de ingestão. A função valida o esquema, verifica identidade, timestamp e
chave de idempotência e grava a leitura no DynamoDB. O sensor recebe sucesso somente
depois da confirmação dessa gravação; erros de validação retornam 4xx e falhas de
persistência retornam 5xx para permitir nova tentativa segura.

### 4.3. Fluxo de alertas

O DynamoDB Streams invoca uma Lambda que consulta uma projeção dos limiares ativos no
DynamoDB, evitando acesso ao RDS no caminho crítico. Quando a condição muda de normal
para crítica, a função cria um alerta idempotente e o publica no SNS. Estado, histerese e
janela de silêncio evitam alertas repetidos a cada leitura. Falhas usam tentativas
limitadas, falha parcial por item e destino durável, com procedimento de replay.

### 4.4. Consulta e arquivamento

Além da série por sensor, tabelas ou índices derivados mantêm o estado mais recente e a
série consultável por `talhao_id + timestamp`. O CloudFront acelera apenas conteúdo
estático; o desempenho das consultas dinâmicas depende do modelo de acesso e da API.

O TTL remove a telemetria ao fim da janela quente, mas não a transfere automaticamente.
Eventos de remoção identificados no DynamoDB Streams são processados por uma Lambda de
arquivamento, que grava os registros no S3 particionados por fazenda, safra e data. O
processo é idempotente, possui destino de falha durável e reconciliação periódica.

### 4.5. Rede e acesso a serviços AWS

- ALB em duas sub-redes públicas; EC2 e RDS em sub-redes privadas.
- Gateway Endpoints gratuitos para S3 e DynamoDB, associados às tabelas de rotas.
- Interface Endpoint para Secrets Manager quando o acesso privado for necessário.
- Lambda de ingestão fora da VPC enquanto depender apenas de serviços gerenciados
  acessíveis por API; qualquer associação futura à VPC deve justificar NAT/endpoints.
- Security Groups permitem somente fluxos entre camadas; NACLs permanecem simples e
  documentadas, incluindo portas efêmeras.

## 5. Capacidades principais

- administração de cadastros e perfis;
- provisionamento, ativação, rotação e revogação de credenciais de sensores;
- ingestão idempotente de umidade, acidez, temperatura e clima;
- painel e série temporal por talhão;
- alertas com estado, deduplicação e auditoria;
- relatórios e histórico de safras;
- observabilidade, backup, restauração e implantação automatizada.

## 6. Premissas, dependências e restrições

- 5.000 sensores iniciais, uma leitura por minuto e crescimento de 20% no primeiro ano.
- Carga média aproximada de 83,3 eventos/s e pico de 500 eventos/s durante 30 minutos.
- Payload de referência de até 4 KiB; cenários diferentes exigem nova medição.
- Limiares são aprovados pela área agronômica e versionados.
- A integração meteorológica possui timeout, cache, limite de consumo e contingência.
- Stack principal: Python, Django REST Framework, IaC e serviços gerenciados AWS.
- Equipe de três integrantes e prazo acadêmico de 20 semanas.
- Orçamento máximo de US$ 1.500 por mês.
- Dados pessoais e dados operacionais das fazendas são protegidos segundo a LGPD e a
  política de classificação da informação.

## 7. Metas de qualidade

| Atributo | Meta comum da baseline |
| -- | -- |
| Disponibilidade | 99,95% mensal para API administrativa e endpoint de ingestão, medidos externamente. |
| Ingestão | p95 entre recebimento e persistência inferior a 80 ms no cenário de referência. |
| Consulta | p95 da API de histórico recente por talhão inferior a 150 ms; primeira visualização em até 3 s. |
| Alerta | p95 entre persistência da leitura crítica e publicação no SNS inferior a 60 s. |
| Durabilidade | Nenhuma leitura aceita é perdida; duplicatas são tratadas por idempotência. |
| Recuperação | RPO transacional inferior a 15 min e RTO sistêmico inferior a 1 h. |
| Segurança | TLS 1.2 ou superior; criptografia KMS em repouso; MFA e RBAC administrativos. |
| Custo | Total mensal inferior a US$ 1.500 e núcleo de ingestão até US$ 4 por milhão de eventos no cenário-base. |

Os métodos de medição, exclusões e critérios completos estão no Documento de
Requisitos Suplementares.

## 8. Aprovação e histórico

| Versão | Data | Status | Descrição | Autor(es) |
| -- | -- | -- | -- | -- |
| 1.0 | 08/09/2026 | Substituída | Versão inicial. | Joao Vitor Donda, Caique Rechuan e Joao Gabriel Meirelles |
| 1.1 | 17/09/2026 | Em revisão | Alinhamento de escopo, atores, fluxos AWS, SLOs, durabilidade, alertas e arquivamento. | Equipe do projeto |

| Papel aprovador | Nome | Data | Decisão |
| -- | -- | -- | -- |
| Arquiteto de Soluções | | | Pendente |
| Professor responsável | | | Pendente |
