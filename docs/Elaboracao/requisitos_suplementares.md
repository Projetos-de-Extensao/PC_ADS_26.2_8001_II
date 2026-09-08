---
id: requisitos_suplementares
title: Requisitos Suplementares
---

# Documento de Requisitos Suplementares (v1.0)

**Projeto**: Lavoura Inteligente<br>
**Fase**: Projeto de Cloud — Fase de Inception<br>
**Data**: 08/09/2026<br>
**Status**: Versão inicial para validação arquitetural

## 1. Propósito e escopo

Este documento define os requisitos não-funcionais, os objetivos de nível de serviço
(SLOs), o acordo de nível de serviço (SLA) e as condições operacionais da plataforma
Lavoura Inteligente.

O escopo inclui:

- portal administrativo e API transacional em Django REST Framework;
- ingestão de telemetria de sensores por API Gateway e AWS Lambda;
- persistência transacional em Amazon RDS PostgreSQL;
- persistência de telemetria em Amazon DynamoDB;
- motor de alertas orientado a eventos via DynamoDB Streams e Amazon SNS;
- arquivos históricos e conteúdo estático em Amazon S3 e Amazon CloudFront;
- rede, segurança, observabilidade, backup e pipeline de CI/CD na AWS.

Não fazem parte deste documento a implementação do código da aplicação, o desenho
detalhado da VPC ou a contratação do serviço externo de dados meteorológicos.

## 2. Contexto e restrições

| Item | Premissa ou restrição |
| -- | -- |
| Escala inicial | 5.000 sensores monitorados |
| Frequência de telemetria | Um evento por sensor a cada 60 segundos |
| Pico de ingestão | Pelo menos 500 eventos por segundo |
| Stack obrigatória | Python, Django REST Framework e serviços gerenciados AWS |
| Equipe | Três pessoas entre desenvolvimento e DevOps |
| Orçamento | Máximo de US$ 1.500 por mês |
| Regulamentação | Lei Geral de Proteção de Dados (LGPD) |
| Crescimento esperado | 20% ao ano |

## 3. Definições e indicadores

- **SLA**: compromisso formal de nível de serviço com o cliente.
- **SLO**: objetivo mensurável que orienta o serviço.
- **SLI**: indicador observado para verificar um SLO.
- **p95**: valor abaixo do qual estão 95% das medições.
- **RPO**: máximo de dados que podem ser perdidos após uma falha.
- **RTO**: tempo máximo para restaurar o serviço.
- **MTTR**: tempo médio para reparar ou restaurar o serviço.
- **DLQ**: fila de mensagens mortas, usada para reprocessar payloads que falham na
  validação em vez de descartá-los.

## 4. Requisitos de desempenho e capacidade

| ID | Requisito | Critério de aceitação |
| -- | -- | -- |
| RNF-PER-01 | A ingestão deve processar telemetria em tempo real. | p95 do tempo entre recebimento e persistência menor que 80 ms em teste de carga. |
| RNF-PER-02 | A plataforma deve suportar a carga de pico. | Processar pelo menos 500 eventos por segundo sem perda e sem erro superior a 1%. |
| RNF-PER-03 | O painel do agrônomo deve responder rapidamente. | p95 das consultas ao histórico recente de um talhão menor que 150 ms em horário de pico. |
| RNF-PER-04 | Os painéis devem carregar de forma adequada ao operador. | Primeira visualização disponível em até 3 segundos em condições normais. |
| RNF-PER-05 | O alerta crítico de irrigação deve chegar ao produtor quase em tempo real. | Intervalo entre a leitura crítica ser gravada e o alerta ser publicado no Amazon SNS menor que 60 segundos. |
| RNF-CAP-01 | A capacidade deve acompanhar o crescimento do parque de sensores. | Escalar para 6.000 sensores sem alteração estrutural da solução. |
| RNF-CAP-02 | A ingestão deve ser isolada do portal administrativo. | Teste de pico de telemetria não pode elevar a taxa de erro da API administrativa acima de 1%. |

Medição: CloudWatch, métricas do API Gateway e testes de carga controlados. As medições
devem registrar percentis, taxa de erro, throughput e cenário utilizado.

## 5. Requisitos de disponibilidade e confiabilidade

| ID | Requisito | Critério de aceitação |
| -- | -- | -- |
| RNF-CON-01 | A API administrativa deve ter disponibilidade mensal de 99,95%. | Downtime não planejado inferior a aproximadamente 22 minutos em uma janela de 30 dias. |
| RNF-CON-02 | O endpoint de ingestão deve ter disponibilidade mensal de 99,9%. | Downtime não planejado inferior a aproximadamente 43 minutos em uma janela de 30 dias. |
| RNF-CON-03 | A solução deve tolerar falha de uma Zona de Disponibilidade. | O serviço permanece operacional ou é restaurado automaticamente após falha de uma AZ. |
| RNF-CON-04 | O RPO para dados transacionais deve ser menor que 15 minutos. | Exercício de recuperação comprova perda inferior a 15 minutos. |
| RNF-CON-05 | O RTO de uma indisponibilidade catastrófica deve ser menor que 1 hora. | Ambiente restaurado e validado em até 60 minutos durante teste de recuperação. |
| RNF-CON-06 | O MTTR de incidentes prioritários deve ser menor que 30 minutos. | O histórico de incidentes P1 registra média inferior a 30 minutos após a operação estabilizada. |
| RNF-CON-07 | Nenhuma leitura de telemetria aceita pelo endpoint pode ser perdida. | Payloads que falharem na validação são encaminhados a uma DLQ para reprocessamento, nunca descartados silenciosamente. |

Diretriz: utilizar, quando compatível com o orçamento, EC2 com Auto Scaling, RDS
Multi-AZ, backups automáticos, DynamoDB com recuperação point-in-time e infraestrutura
reproduzível por templates ou scripts.

## 6. Requisitos de segurança e privacidade

| ID | Requisito | Critério de aceitação |
| -- | -- | -- |
| RNF-SEG-01 | Toda comunicação externa deve ser protegida. | APIs públicas aceitam somente HTTPS/TLS na porta 443. |
| RNF-SEG-02 | Dados em repouso devem ser criptografados. | RDS, DynamoDB, S3 e backups utilizam criptografia gerenciada por AWS KMS. |
| RNF-SEG-03 | O acesso administrativo deve exigir autenticação forte. | MFA habilitado para contas administrativas e RBAC aplicado a Admin, Agrônomo e Auditor. |
| RNF-SEG-04 | O princípio do menor privilégio deve ser aplicado. | Cada serviço utiliza uma IAM role específica, sem credenciais compartilhadas. |
| RNF-SEG-05 | Segredos não podem ser armazenados no código. | Credenciais e chaves ficam no AWS Secrets Manager e não aparecem no repositório ou nos logs. |
| RNF-SEG-06 | A plataforma deve permitir auditoria. | Acessos administrativos e transações críticas são registrados, protegidos contra alteração e retidos conforme política aprovada. |
| RNF-SEG-07 | O tratamento de dados deve observar a LGPD. | Dados pessoais de produtores e agrônomos são minimizados, têm finalidade definida, acesso controlado e política de retenção documentada. |

## 7. Requisitos de operação e observabilidade

| ID | Requisito | Critério de aceitação |
| -- | -- | -- |
| RNF-OPS-01 | A saúde dos serviços deve ser monitorada continuamente. | Dashboard CloudWatch exibe disponibilidade, latência p95, throughput, erros e uso de recursos. |
| RNF-OPS-02 | Incidentes devem gerar alertas acionáveis. | Alarmes para indisponibilidade, erro, latência e custo encaminham notificações à equipe responsável. |
| RNF-OPS-03 | Logs devem ser centralizados. | 100% das requisições administrativas e eventos de segurança possuem correlação e retenção definida. |
| RNF-OPS-04 | Backups devem ser automatizados. | RDS possui backup diário com retenção de 30 dias; DynamoDB possui backup e recuperação point-in-time habilitados. |
| RNF-OPS-05 | A recuperação deve ser praticada. | Procedimento de restore é documentado e testado pelo menos uma vez por ciclo de entrega. |
| RNF-OPS-06 | A manutenção deve ser controlada. | Manutenções programadas ocorrem fora do horário comercial e não excedem 2 horas por mês. |

## 8. Requisitos de manutenibilidade e entrega

| ID | Requisito | Critério de aceitação |
| -- | -- | -- |
| RNF-MAN-01 | O deploy deve ser automatizado. | CodePipeline e CodeBuild executam validações e publicam uma versão aprovada em até 10 minutos. |
| RNF-MAN-02 | O rollback deve ser rápido. | Uma versão estável pode ser restaurada em até 5 minutos após decisão de rollback. |
| RNF-MAN-03 | Mudanças devem ser rastreáveis. | Cada deploy registra versão, autor, testes, horário e resultado. |
| RNF-MAN-04 | A solução deve ser documentada. | Runbooks cobrem deploy, rollback, incidentes, backup e recuperação antes da entrega. |
| RNF-MAN-05 | A infraestrutura deve ser reproduzível. | Componentes críticos podem ser recriados a partir de configuração versionada. |

## 9. Requisitos de usabilidade

| ID | Requisito | Critério de aceitação |
| -- | -- | -- |
| RNF-USA-01 | O agrônomo deve visualizar a saúde do ambiente e dos talhões. | Painel apresenta status da ingestão, latência, throughput e alertas ativos sem depender de consulta manual a logs. |
| RNF-USA-02 | A API deve ser compreensível para consumidores autorizados. | Especificação OpenAPI/Swagger atualizada acompanha os endpoints publicados. |
| RNF-USA-03 | Mensagens de erro devem orientar a ação. | Erros retornam código HTTP adequado, identificador de correlação e mensagem sem expor segredos. |

## 10. Requisitos de custo

| ID | Requisito | Critério de aceitação |
| -- | -- | -- |
| RNF-CUS-01 | O custo mensal total deve respeitar o orçamento. | Projeção e faturamento mensal permanecem abaixo de US$ 1.500. |
| RNF-CUS-02 | O custo deve ser acompanhado continuamente. | AWS Budgets gera alerta em 80%, 90% e 100% do orçamento mensal. |
| RNF-CUS-03 | A ingestão deve ser economicamente escalável. | Custo médio alvo por evento inferior a US$ 0,001, validado por estimativa de uso. |
| RNF-CUS-04 | Recursos devem ser dimensionados conforme a demanda. | Auto Scaling, políticas de retenção (TTL do DynamoDB) e classes de armazenamento do S3 são revisados a cada ciclo. |

Trade-off obrigatório: disponibilidade, desempenho e segurança não devem ser aprovados
sem registrar o impacto correspondente no orçamento.

## 11. SLA e responsabilidades

O SLA inicial da API administrativa e do portal de gestão de safras estabelece 99,95%
de disponibilidade mensal, medido por chamadas sintéticas HTTPS a partir de uma região
de referência. Manutenções comunicadas com antecedência e dentro da janela aprovada não
entram no cálculo, conforme contrato definitivo.

| Responsável | Obrigações principais |
| -- | -- |
| **AWS** | Disponibilidade dos serviços gerenciados e da infraestrutura física subjacente, conforme os SLAs de cada serviço contratado. |
| **Lavoura Inteligente** | Código, configuração, IAM, dados, monitoramento, backups, testes e resposta a incidentes sob seu controle. |
| **Equipe de projeto** | Validar metas, registrar evidências, controlar custos e aprovar mudanças nos requisitos. |

Descumprimentos devem gerar registro de incidente, análise de causa e plano de ação.
Penalidades ou créditos comerciais serão definidos no contrato do serviço e não são
assumidos como requisito técnico deste documento.

## 12. Dependências, riscos e decisões pendentes

| Item | Impacto | Tratamento |
| -- | -- | -- |
| Custo real de Multi-AZ e observabilidade | Pode exceder US$ 1.500/mês | Validar no AWS Pricing Calculator antes do desenho final. |
| Meta de latência p95 menor que 80 ms | Depende de região, payload e processamento | Definir região, tamanho de mensagem e cenário do teste de carga. |
| RPO do DynamoDB | Backup não substitui toda estratégia de continuidade | Definir política de exportação, retenção e procedimento de restore. |
| Definição dos limiares críticos por cultura | Sem os limiares corretos, o motor de alertas gera falsos positivos ou negativos | Validar os limiares com a área agronômica antes da implantação. |
| Dados pessoais e operacionais das fazendas | Risco regulatório (LGPD) e de exposição de informação comercial sensível | Criar inventário de dados, controles de acesso e política de retenção. |
| Integração com dados meteorológicos externos | Dependência externa e custo variável | Definir limites, timeout, cache e comportamento de contingência. |

## 13. Critérios de aprovação

O documento será considerado aprovado quando:

- todos os requisitos críticos tiverem métrica e critério de aceitação;
- a arquitetura proposta demonstrar atendimento aos requisitos de desempenho e
  disponibilidade;
- o custo estimado estiver dentro do orçamento ou possuir exceção formal aprovada;
- o plano de segurança e LGPD for revisado pelo responsável de segurança;
- os testes de carga, backup, restore e rollback estiverem planejados.

## 14. Histórico de versões

| Versão | Data | Descrição | Autor(es) |
| -- | -- | -- | -- |
| 1.0 | 08/09/2026 | Criação do Documento de Requisitos Suplementares para o Case 6 — AgTech "Lavoura Inteligente". | Joao Vitor Donda, Caique Rechuan e Joao Gabriel Meirelles |
