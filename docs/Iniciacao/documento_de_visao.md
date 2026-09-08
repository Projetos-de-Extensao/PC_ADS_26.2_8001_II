---
id: documento_de_visao
title: Documento de Visão
---

# Documento de Visão (v1.0)

**Projeto**: Lavoura Inteligente — Plataforma de Telemetria Agrícola<br>
**Case**: 6 — AgTech<br>
**Turma**: PC_ADS_26.2_8001_II<br>
**Fase**: Inception

## 1. Introdução

Este documento descreve as necessidades de negócio, as restrições e os requisitos de
infraestrutura da plataforma Lavoura Inteligente, servindo de guia para o planejamento
arquitetural da solução na nuvem AWS.

### 1.1. Propósito

Definir a visão de escopo e a arquitetura lógica e física para a implantação da
plataforma Lavoura Inteligente na infraestrutura da AWS, demonstrando a viabilidade de
uma arquitetura resiliente, de alta performance e custo otimizado para o monitoramento
em tempo real de lavouras conectadas de grande extensão.

### 1.2. Escopo

O escopo deste projeto de cloud engloba os seguintes componentes e serviços:

1. **Portal Administrativo e API Transacional**: aplicação em Python com Django REST
   Framework para o cadastro de fazendas, talhões, culturas, sensores e agrônomos, além
   da configuração dos limiares que disparam os alertas de irrigação e da emissão de
   relatórios consolidados de safra.
2. **Pipeline Serverless de Ingestão de IoT**: endpoint HTTP de baixo payload para
   receber, de forma assíncrona, a telemetria enviada a cada minuto por milhares de
   sensores de umidade do solo, acidez, temperatura e clima.
3. **Persistência de Dados Híbrida**: armazenamento relacional para as operações de
   negócio e NoSQL para o histórico contínuo de telemetria (séries temporais), com
   arquivamento das safras encerradas em armazenamento de objetos.
4. **Motor de Alertas em Tempo Real**: avaliação contínua das leituras contra os
   limiares críticos de cada cultura e notificação imediata ao produtor.
5. **Infraestrutura de Rede e Segurança**: isolamento lógico dos servidores de aplicação
   e do banco de dados, firewall rígido e gerenciamento seguro de credenciais.
6. **Automação CI/CD**: pipeline de integração e entrega contínua para atualizações
   automáticas e seguras no ambiente de produção.

Está **fora do escopo** desta fase: a fabricação e a homologação do hardware dos
sensores, o acionamento físico e automatizado dos pivôs de irrigação e a previsão
agronômica por modelos de aprendizado de máquina.

### 1.3. Definições, Acrônimos e Abreviações

- **API**: Application Programming Interface
- **VPC**: Virtual Private Cloud (Rede Virtual Privada)
- **RDS**: Relational Database Service (Banco de Dados Relacional Gerenciado)
- **NoSQL**: Not Only SQL (Banco de Dados Não Relacional)
- **IoT**: Internet of Things (Internet das Coisas)
- **TTL**: Time To Live (prazo de expiração automática de um registro)
- **SLA**: Service Level Agreement (Acordo de Nível de Serviço)
- **SLO**: Service Level Objective (Objetivo de Nível de Serviço)
- **RPO**: Recovery Point Objective (Objetivo de Ponto de Recuperação)
- **RTO**: Recovery Time Objective (Objetivo de Tempo de Recuperação)
- **IaC**: Infrastructure as Code (Infraestrutura como Código)
- **Talhão**: menor unidade de manejo de uma lavoura, à qual os sensores são associados

### 1.4. Referências

- AWS Well-Architected Framework (pilares de Excelência Operacional, Segurança,
  Confiabilidade, Eficiência de Performance, Otimização de Custos e Sustentabilidade).
- Lei Geral de Proteção de Dados (LGPD — Lei nº 13.709/2018).
- Documentação oficial do Amazon DynamoDB — modelagem de dados de séries temporais.
- Plano de Ensino da disciplina e roteiro do Case 6 — AgTech "Lavoura Inteligente".

## 2. Posicionamento

### 2.1. Oportunidade de Negócio

A agricultura de precisão avança sobre lavouras cada vez maiores, e a decisão de irrigar
deixou de ser um julgamento visual para se tornar uma decisão movida a dados. Um atraso
de horas em um alerta de umidade crítica do solo custa produtividade na safra e
desperdiça água e energia em irrigações mal dimensionadas. Empresas consolidadas do
agronegócio já possuem os sensores instalados em campo, mas operam sobre plataformas de
dados que não acompanham a volumetria gerada por eles. Existe, portanto, a oportunidade
de entregar uma plataforma que aproveite o parque de sensores já instalado e converta
essa telemetria em decisão imediata de manejo.

### 2.2. Descrição do Problema

| | |
| -- | -- |
| **O problema de...** | Lentidão extrema do banco de dados relacional diante da alta concorrência de escritas simultâneas de séries temporais, com risco de perda de leituras nos picos de ingestão e atrasos de até horas na emissão dos alertas automáticos de irrigação. |
| **Afeta...** | Produtores rurais, agrônomos de campo e a equipe de operação da plataforma. |
| **Cujo impacto é...** | Irrigação aplicada tarde ou em excesso, perda de produtividade da safra, desperdício de água e energia, painéis desatualizados que levam a decisões de manejo equivocadas e desgaste da confiança do produtor na plataforma. |
| **Uma solução bem-sucedida incluiria...** | Uma arquitetura desacoplada na AWS que separe o fluxo de alta frequência de escrita da telemetria do fluxo administrativo transacional, sustentada por um armazenamento que escale horizontalmente, de modo que o alerta crítico chegue ao produtor em segundos e o portal permaneça responsivo mesmo sob o pico de ingestão. |

### 2.3. Posicionamento do Produto

Para empresas do agronegócio que operam lavouras conectadas de grande extensão, a
**Lavoura Inteligente** é uma plataforma de telemetria e alertas agrícolas que entrega
alertas críticos de irrigação em menos de um minuto e painéis consolidados para os
agrônomos de campo. Diferente da arquitetura atual, que grava séries temporais de
sensores em um banco relacional e degrada sob carga, nossa solução combina uma ingestão
serverless elástica com um armazenamento NoSQL de escrita distribuída, mantendo o portal
administrativo isolado do pico de telemetria.

## 3. Descrição dos Stakeholders e Usuários

| Stakeholder (Perfil) | Necessidade Primária | Expectativa na Nuvem (AWS) |
| -- | -- | -- |
| **Agrônomos de campo** | Acompanhar a condição do solo por talhão e decidir o manejo com dados atuais. | Painéis que carreguem o histórico recente do talhão instantaneamente, mesmo em conexão móvel no campo. |
| **Produtores rurais** | Receber o alerta de irrigação a tempo de agir sobre a lavoura. | Notificação imediata e confiável, sem depender de o produtor estar com o painel aberto. |
| **Gestores de operação agrícola** | Enxergar o estado consolidado de todas as fazendas e comparar safras. | Relatórios de safra construídos sobre o histórico completo, sem impacto na ingestão em andamento. |
| **Diretoria Financeira (CFO)** | Manter o custo da nuvem dentro do orçamento aprovado. | Custo previsível e proporcional ao volume de telemetria, com alertas de faturamento e recursos corretamente dimensionados. |
| **Segurança da Informação (CISO)** | Proteger os dados operacionais das fazendas e os dados pessoais dos usuários. | Criptografia em trânsito e em repouso, rede blindada, credenciais fora do código-fonte e rastreabilidade de acessos. |
| **Corpo Docente (TI)** | Validar a qualidade técnica da arquitetura proposta pelo grupo. | Solução justificada à luz do AWS Well-Architected Framework e documentada com clareza no DAS. |

## 4. Visão Geral da Solução

### 4.1. Perspectiva do Produto

A Lavoura Inteligente operará como um ecossistema nativo em nuvem de formato híbrido. A
aplicação principal em Django REST Framework atenderá o portal administrativo e os
painéis web via HTTPS. Em paralelo, um fluxo de ingestão serverless e autônomo receberá
a telemetria enviada pelos sensores instalados nos talhões, gravando-a em um banco NoSQL
dimensionado para escrita contínua. Os dois fluxos compartilham os dados, mas não
compartilham capacidade: um pico de telemetria não derruba o portal, e uma consulta
pesada no portal não atrasa a ingestão.

### 4.2. Funcionalidades Principais

- **Portal de Administração**: cadastro de fazendas, talhões, culturas, sensores e
  usuários, e configuração dos limiares críticos por cultura.
- **Ingestão Contínua de Telemetria**: recepção, validação e sanitização das leituras de
  umidade do solo, acidez, temperatura e clima enviadas a cada minuto.
- **Motor de Alertas de Irrigação**: avaliação das leituras contra os limiares
  configurados e notificação imediata ao produtor responsável.
- **Painel de Monitoramento por Talhão**: visualização das séries temporais recentes e
  do estado atual de cada talhão para os agrônomos de campo.
- **Histórico e Relatórios de Safra**: consolidação periódica das leituras e consulta ao
  histórico de safras encerradas.

### 4.3. Suposições e Dependências

- **Suposições**: os sensores já instalados possuem conectividade de rede para o envio
  da telemetria e são capazes de emitir requisições HTTPS autenticadas; o parque atual
  gira em torno de alguns milhares de sensores enviando uma leitura por minuto; a equipe
  do projeto tem proficiência prática em configurar a infraestrutura pelo Console AWS e
  por práticas de IaC.
- **Dependências**: disponibilidade de uma conta AWS de laboratório para a implantação;
  definição, pela área agronômica, dos limiares críticos de cada cultura; integração com
  serviço externo de dados meteorológicos para complementar as leituras de clima.

## 5. Recursos do Produto (Arquitetura AWS)

| Serviço AWS | Papel na Arquitetura | Justificativa Técnica (Por que usar?) |
| -- | -- | -- |
| **Amazon VPC** | Isolamento de rede e firewalls | Sub-redes públicas para o load balancer e o API Gateway, e sub-redes privadas para EC2 e RDS. Security Groups atuam como firewall de instância (stateful) e NACLs como firewall de sub-rede (stateless), restringindo o tráfego às portas estritamente necessárias (443 e 5432). |
| **Amazon EC2** | Servidor de aplicação do portal | Instância (ex.: t3.medium) hospedando a API administrativa em Django REST sob Gunicorn com Nginx como proxy reverso, integrada a um Auto Scaling Group. Mantém o portal fora do caminho crítico da ingestão. |
| **Amazon RDS (PostgreSQL)** | Banco relacional transacional | Persistência dos dados de negócio (fazendas, talhões, culturas, sensores, usuários e limiares de alerta), que exigem integridade referencial e transações ACID. Configurado em Multi-AZ para alta disponibilidade e failover automático. |
| **Amazon DynamoDB** | Banco NoSQL de telemetria | Absorve a escrita contínua das séries temporais dos sensores. A chave de partição `sensor_id` distribui a carga entre partições e a chave de ordenação `timestamp` mantém a leitura por janela de tempo eficiente, eliminando a contenção de escrita que hoje derruba o banco relacional e escalando horizontalmente para bilhões de registros. |
| **Amazon DynamoDB Streams + AWS Lambda** | Motor de alertas orientado a eventos | Cada gravação de telemetria emite um evento no stream, consumido por uma função que compara a leitura ao limiar da cultura e dispara o alerta. O alerta nasce do próprio fluxo de escrita, o que derruba a latência de horas para segundos. |
| **AWS Lambda + Amazon API Gateway** | Pipeline serverless de ingestão | O API Gateway expõe a rota REST autenticada em que os sensores publicam a telemetria, e o Lambda valida, sanitiza e grava o dado no DynamoDB. Escala de zero a milhares de execuções concorrentes em segundos, sem onerar as instâncias EC2. |
| **Amazon SNS** | Entrega dos alertas | Publica os alertas de irrigação para os canais de notificação dos produtores, desacoplando a regra de negócio do meio de entrega. |
| **Amazon S3 + Amazon CloudFront** | Camada fria e distribuição do front-end | O S3 guarda, com baixo custo por GB, os arquivos históricos e consolidados das safras encerradas, recebidos por expiração via TTL no DynamoDB. O CloudFront distribui os ativos estáticos dos painéis com HTTPS e cache na borda, eliminando esse tráfego das instâncias EC2. |
| **AWS CodePipeline + CodeBuild** | Automação e pipeline CI/CD | Dispara os testes automatizados a partir do repositório no GitHub e atualiza a aplicação de forma automatizada, mitigando erros manuais de implantação. |
| **Amazon CloudWatch** | Observabilidade e alertas operacionais | Consolida métricas (latência do API Gateway, erros e duração das funções Lambda, capacidade consumida no DynamoDB, CPU da EC2) e logs para auditoria, com alarme de taxa de erro na ingestão. |
| **AWS Secrets Manager** | Gerenciamento seguro de credenciais | Centraliza a credencial de conexão do RDS e as chaves de integração externas, injetadas dinamicamente na aplicação para evitar segredos expostos no código-fonte. |

## 6. Restrições do Projeto

- **Orçamentária**: o custo operacional total da infraestrutura está fixado em no máximo
  **US$ 1.500,00 por mês**, o que torna obrigatório o dimensionamento correto dos
  recursos e a adoção do modelo de pagamento por uso na camada de ingestão.
- **Prazo**: o cronograma acadêmico impõe **20 semanas** para a conclusão de todas as
  fases, da Iniciação à Elaboração, Construção e defesa final na Transição.
- **Tecnológica**: a aplicação web principal deve utilizar Django REST Framework em
  Python, e toda a implantação produtiva deve ocorrer dentro de uma conta sandbox da AWS,
  privilegiando serviços gerenciados.
- **Segurança e Compliance**: nenhum dado de identificação pessoal de produtores e
  agrônomos pode trafegar ou ser armazenado sem criptografia em trânsito e em repouso. O
  sistema deve atender às exigências básicas da LGPD, e os dados operacionais das
  fazendas são tratados como informação comercial sensível.
- **Pessoal**: o time é composto por **3 integrantes**, que acumulam os papéis de
  desenvolvimento backend, administração de infraestrutura e documentação — o que reforça
  a preferência por serviços gerenciados em vez de componentes autogerenciados.

## 7. Atributos de Qualidade (SLAs e SLOs)

- **Disponibilidade**: o endpoint de ingestão e o portal administrativo devem manter um
  SLA global de **99,95%** de uptime (cerca de 4,3 horas de indisponibilidade permitidas
  por ano), alcançado com sub-redes distribuídas em pelo menos duas Zonas de
  Disponibilidade, EC2 sob Auto Scaling e RDS em Multi-AZ.
- **Performance (Latência)**: o endpoint serverless de ingestão deve responder em menos
  de **80ms no percentil 95** das escritas. O painel do agrônomo deve carregar a série
  temporal recente de um talhão em menos de **150ms**, apoiado nas consultas indexadas do
  DynamoDB e no cache do CloudFront.
- **Latência do Alerta**: o intervalo entre a leitura crítica chegar ao endpoint e o
  alerta ser publicado ao produtor deve ser inferior a **60 segundos**, contra as horas
  de atraso da solução atual.
- **Durabilidade da Ingestão**: nenhuma leitura aceita pelo endpoint pode ser perdida.
  Payloads que falharem na validação são encaminhados a uma fila de mensagens mortas
  (DLQ) para reprocessamento, em vez de descartados silenciosamente.
- **Segurança (Criptografia)**: toda comunicação pública ocorre exclusivamente sob
  HTTPS/TLS na porta 443. Os dados armazenados no RDS, no DynamoDB e no S3 são
  criptografados em repouso com o AWS KMS.
- **Continuidade de Negócio (Backup e DR)**:
    - **RPO**: no máximo **15 minutos** de perda de dados, garantido por backups
      automáticos e point-in-time recovery habilitados no RDS e no DynamoDB.
    - **RTO**: recuperação total em menos de **1 hora** diante de indisponibilidade
      sistêmica, apoiada na reconstrução do ambiente por scripts de IaC.
- **Custo-eficiência**: o Auto Scaling escala as instâncias EC2 horizontalmente apenas
  quando o uso agregado de CPU ultrapassa 75% e reduz ao mínimo de uma instância nos
  períodos de baixa demanda. O TTL do DynamoDB expira a telemetria bruta após a janela de
  consulta quente, transferindo o histórico para o S3 e mantendo a tabela enxuta.

## 8. Aprovação e Histórico de Versões

| Versão | Data | Descrição da Alteração | Autor(es) |
| -- | -- | -- | -- |
| 1.0 | 08/09/2026 | Elaboração inicial do Documento de Visão para o Case 6 — AgTech "Lavoura Inteligente". | Joao Vitor Donda, Caique Rechuan e Joao Gabriel Meirelles |
