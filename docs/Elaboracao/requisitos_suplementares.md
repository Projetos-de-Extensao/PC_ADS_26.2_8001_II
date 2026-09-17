---
id: requisitos_suplementares
title: Requisitos Suplementares
---

# Documento de Requisitos Suplementares (v1.1)

**Projeto**: Lavoura Inteligente<br>
**Fase**: Elaboração<br>
**Data**: 17/09/2026<br>
**Status**: Em revisão

## 1. Propósito e escopo

Este documento define requisitos não funcionais, SLOs, regras operacionais e critérios
de aceitação. Requisitos funcionais são identificados no Levantamento de Requisitos e
ligados aos casos de uso pela matriz de rastreabilidade.

## 2. Cenário de referência

| Item | Valor adotado para dimensionamento e teste |
| -- | -- |
| Região | Definida no DAS antes do teste; todas as evidências registram a região usada. |
| Escala inicial | 5.000 sensores. |
| Frequência | Uma leitura por sensor a cada 60 segundos. |
| Carga média | Aproximadamente 83,3 eventos por segundo. |
| Pico | 500 eventos por segundo durante 30 minutos. |
| Payload | Até 4 KiB, incluindo metadados. |
| Volume mensal | Aproximadamente 216 milhões de eventos em 30 dias. |
| Crescimento | 20% no primeiro ano, chegando a 6.000 sensores. |
| Equipe | Três integrantes entre desenvolvimento, infraestrutura e documentação. |
| Orçamento | Até US$ 1.500 por mês. |

Qualquer teste com valores diferentes deve registrar payload, duração, concorrência,
região, aquecimento, volume e resultado para continuar reproduzível.

## 3. Definições de medição

- **Leitura recebida**: requisição que chegou ao API Gateway.
- **Leitura válida**: requisição autenticada que passou pelo esquema e pelas regras.
- **Leitura aceita**: leitura válida cuja gravação durável foi confirmada antes da
  resposta 2xx. Payload rejeitado com 4xx não é leitura aceita.
- **Disponibilidade**: proporção de sondas HTTPS sintéticas válidas que recebem resposta
  esperada dentro do limite de tempo, medida externamente a cada minuto.
- **Latência de ingestão**: tempo entre a entrada no API Gateway e a confirmação da
  gravação no DynamoDB.
- **Latência de alerta**: tempo entre a gravação da leitura crítica e a publicação
  confirmada no SNS. Entrega pelo canal é medida separadamente quando houver confirmação.
- **p95**: valor abaixo do qual ficam 95% das medições válidas.
- **RPO/RTO/MTTR**: perda máxima de dados, tempo máximo de recuperação e tempo médio de
  restauração.

## 4. Desempenho e capacidade

| ID | Requisito | Critério de aceitação |
| -- | -- | -- |
| RNF-PER-01 | A ingestão deve persistir telemetria em tempo real. | p95 inferior a 80 ms no cenário de referência. |
| RNF-PER-02 | A plataforma deve suportar o pico. | 500 eventos/s durante 30 min, sem perda de leitura aceita e com erro de servidor inferior a 1%. |
| RNF-PER-03 | O histórico recente por talhão deve responder rapidamente. | p95 da API inferior a 150 ms no pico, sem contar a rede do dispositivo. |
| RNF-PER-04 | A primeira visualização do painel deve ser utilizável. | Conteúdo principal visível em até 3 s em perfil de rede móvel definido no teste. |
| RNF-PER-05 | Alertas críticos devem ser publicados quase em tempo real. | p95 inferior a 60 s entre persistência e confirmação de publicação no SNS. |
| RNF-CAP-01 | A solução deve absorver o crescimento do primeiro ano. | 6.000 sensores sem mudança estrutural e sem violação dos SLOs. |
| RNF-CAP-02 | A ingestão deve permanecer isolada do portal. | O teste de pico não aumenta erros da API administrativa acima de 1% nem viola seu p95 acordado. |
| RNF-CAP-03 | Consultas por talhão não podem fazer varredura integral. | Evidência mostra Query por chave/índice ou tabela derivada, sem Scan da tabela de telemetria. |

## 5. Disponibilidade, durabilidade e recuperação

| ID | Requisito | Critério de aceitação |
| -- | -- | -- |
| RNF-CON-01 | API administrativa e endpoint de ingestão devem estar disponíveis. | Cada serviço atinge 99,95% por mês, aproximadamente 22 min de indisponibilidade não planejada em 30 dias. |
| RNF-CON-02 | A camada administrativa deve tolerar falha de uma AZ. | ALB e no mínimo duas EC2, uma por AZ; teste comprova continuidade ou reposição dentro do SLO. |
| RNF-CON-03 | Dados transacionais devem possuir RPO inferior a 15 min. | Exercício de recuperação comprova o limite. |
| RNF-CON-04 | O serviço deve possuir RTO sistêmico inferior a 1 h. | Ambiente reconstruído por IaC e validado em até 60 min. |
| RNF-CON-05 | Incidentes P1 devem possuir MTTR inferior a 30 min. | Média mensal calculada sobre incidentes encerrados, com causa e linha do tempo registradas. |
| RNF-CON-06 | Nenhuma leitura aceita pode ser perdida. | Testes de falha confirmam persistência; 4xx não conta como aceite e 5xx permite retry idempotente. |
| RNF-CON-07 | Reprocessamento não pode duplicar efeitos. | A mesma chave de idempotência não cria segunda leitura nem segundo alerta. |
| RNF-CON-08 | Falhas do Streams devem ser recuperáveis. | Mapeamento usa tentativas limitadas, idade máxima, falha parcial, bisect e destino durável; runbook comprova replay. |
| RNF-CON-09 | O arquivamento deve ser verificável. | Contagem/hash por partição comprova que itens removidos por TTL foram gravados no S3 ou enviados ao destino de falha. |

Manutenções programadas, comunicadas com 72 horas e limitadas a 2 horas por mês,
são informadas separadamente. O relatório publica disponibilidade bruta e disponibilidade
contratual para que a exclusão não oculte o impacto ao usuário.

## 6. Segurança e privacidade

| ID | Requisito | Critério de aceitação |
| -- | -- | -- |
| RNF-SEG-01 | Comunicações externas devem ser protegidas. | Somente HTTPS com TLS 1.2 ou superior; HTTP redireciona ou é recusado. |
| RNF-SEG-02 | Dados em repouso devem ser criptografados. | RDS, DynamoDB, S3, logs e backups usam chaves AWS KMS conforme classificação. |
| RNF-SEG-03 | Acesso administrativo deve exigir autenticação forte. | MFA e RBAC para Administrador, Agrônomo, Gestor e Auditor. |
| RNF-SEG-04 | Serviços devem seguir menor privilégio. | Role específica por componente, sem curinga amplo sem justificativa aprovada. |
| RNF-SEG-05 | Segredos não podem estar em código ou logs. | Varredura do repositório e amostra de logs sem credenciais; segredos no Secrets Manager. |
| RNF-SEG-06 | Ações críticas devem ser auditáveis. | Login, alteração de limiar, credencial de sensor, permissão e exclusão possuem autor, data e correlação. |
| RNF-SEG-07 | O tratamento deve observar a LGPD. | Inventário de dados, finalidade/base legal, minimização, retenção, controle de acesso e processo para direitos do titular documentados. |
| RNF-SEG-08 | Sensores devem possuir identidade revogável. | Credencial individual ou identidade equivalente, rotação e revogação sem afetar outros sensores. |
| RNF-SEG-09 | Replays e dados fora da janela devem ser controlados. | Timestamp, nonce/idempotency key e janela de aceitação validados. |

## 7. Operação e observabilidade

| ID | Requisito | Critério de aceitação |
| -- | -- | -- |
| RNF-OPS-01 | A saúde deve ser observável. | Dashboard exibe disponibilidade, p95, throughput, erros, atraso do Streams, destino de falha e custo. |
| RNF-OPS-02 | Incidentes devem gerar alertas acionáveis. | Alarmes possuem limiar, janela, responsável, severidade e runbook. |
| RNF-OPS-03 | Logs devem ser correlacionáveis. | 100% das requisições administrativas e eventos de segurança possuem correlation ID e retenção definida. |
| RNF-OPS-04 | Backups devem ser automatizados. | RDS com backup/PITR e retenção de 30 dias; DynamoDB com PITR; configuração verificada diariamente. |
| RNF-OPS-05 | Recuperação deve ser praticada. | Restore completo testado ao menos uma vez por ciclo de entrega. |
| RNF-OPS-06 | Falhas devem gerar aprendizagem. | Incidente P1 possui análise de causa, impacto, ação e responsável. |
| RNF-OPS-07 | A integração meteorológica deve degradar com segurança. | Timeout, retry limitado, circuit breaker/cache e sinalização de dado desatualizado testados. |

## 8. Manutenibilidade e entrega

| ID | Requisito | Critério de aceitação |
| -- | -- | -- |
| RNF-MAN-01 | Deploy deve ser automatizado. | Pipeline valida e publica versão aprovada em até 10 min. |
| RNF-MAN-02 | Rollback deve ser rápido. | Versão estável restaurada em até 5 min após a decisão. |
| RNF-MAN-03 | Mudanças devem ser rastreáveis. | Deploy registra commit, autor, testes, aprovação, horário e resultado. |
| RNF-MAN-04 | Operação deve possuir runbooks. | Deploy, rollback, incidente, replay, backup, restore e rotação de credenciais documentados. |
| RNF-MAN-05 | Infraestrutura deve ser reproduzível. | Componentes críticos recriados por IaC versionada. |
| RNF-MAN-06 | Documentação deve ser publicável. | `mkdocs build --strict` passa no CI antes do deploy. |

## 9. Usabilidade e API

| ID | Requisito | Critério de aceitação |
| -- | -- | -- |
| RNF-USA-01 | O agrônomo deve identificar rapidamente o estado dos talhões. | Painel mostra atualização, qualidade/frescor do dado e alertas ativos sem exigir leitura de logs. |
| RNF-USA-02 | A API deve ser compreensível. | OpenAPI atualizada e validada no CI acompanha os endpoints. |
| RNF-USA-03 | Erros devem orientar a ação. | Código HTTP correto, correlation ID e mensagem segura; 4xx e 5xx são distinguíveis. |
| RNF-USA-04 | Alertas repetidos devem ser controlados. | Estado, histerese e janela de silêncio são configuráveis e auditáveis. |

## 10. Custo

| ID | Requisito | Critério de aceitação |
| -- | -- | -- |
| RNF-CUS-01 | O custo total deve respeitar o orçamento. | Estimativa e faturamento ficam abaixo de US$ 1.500/mês. |
| RNF-CUS-02 | O custo deve ser acompanhado. | AWS Budgets alerta em 80%, 90% e 100%; anomalias têm responsável. |
| RNF-CUS-03 | A ingestão deve ser economicamente escalável. | API Gateway, Lambda, DynamoDB, Streams e logs custam no máximo US$ 4 por milhão de eventos no cenário-base. |
| RNF-CUS-04 | A estimativa deve ser reproduzível. | Planilha/Calculator registra região, eventos, bytes, retenção, transferência, logs, NAT/endpoints e data dos preços. |
| RNF-CUS-05 | Recursos devem ser revistos por ciclo. | Capacidade, ASG, TTL, classes S3, logs e endpoints têm decisão registrada. |

O custo total é a restrição principal. O valor por milhão de eventos é um limite
da camada de ingestão, não substitui a validação do total mensal.

## 11. Regras de alerta e arquivamento

| ID | Regra | Critério de aceitação |
| -- | -- | -- |
| RNF-ALT-01 | Um alerta deve possuir chave idempotente. | Reprocessar o mesmo evento não publica segundo alerta. |
| RNF-ALT-02 | Estado crítico persistente não deve gerar spam. | Nova notificação respeita janela configurada ou mudança de severidade. |
| RNF-ALT-03 | Recuperação deve ser comunicada. | Transição de crítico para normal gera evento de resolução. |
| RNF-ALT-04 | Ausência de limiar deve ser visível. | Evento não é descartado; métrica e alerta operacional identificam cultura/talhão sem regra. |
| RNF-ARQ-01 | TTL não pode ser tratado como transferência automática. | Remoção TTL aciona fluxo explícito e idempotente de gravação no S3. |
| RNF-ARQ-02 | Arquivo deve ser consultável e governado. | Objetos são particionados, criptografados, versionados e possuem ciclo de vida/retenção. |

## 12. SLA e responsabilidades

O SLA inicial é de 99,95% mensal para a API administrativa e, separadamente, para o
endpoint de ingestão. O indicador vem de sondas HTTPS externas a cada minuto. O relatório
mensal identifica indisponibilidade planejada, não planejada, dependências e violações.

| Responsável | Obrigações principais |
| -- | -- |
| AWS | Serviços gerenciados e infraestrutura física segundo os respectivos SLAs. |
| Equipe Lavoura Inteligente | Código, configuração, IAM, dados, testes, custos, backup e resposta a incidentes. |
| Área agronômica | Aprovar limiares, histerese e regras de manejo. |
| Responsável de segurança | Aprovar inventário de dados, acesso, retenção e controles LGPD. |

## 13. Dependências e decisões pendentes

| Item | Tratamento obrigatório antes da aprovação |
| -- | -- |
| Região AWS | Registrar no DAS e repetir nos testes e custos. |
| Canal de alerta | Definir canal, confirmação de entrega, custo e contingência. |
| Retenção quente/fria | Definir dias no DynamoDB e anos no S3 segundo negócio/LGPD. |
| Limiares agronômicos | Aprovar valores, versão, histerese e vigência. |
| Dados meteorológicos | Definir fornecedor, contrato, limites, cache e fallback. |
| Modelo por talhão | Validar índice/tabela derivada com teste de carga. |
| Estimativa de custo | Validar no AWS Pricing Calculator antes do desenho final. |

## 14. Critérios de aprovação

Esta versão pode ser aprovada quando:

- todos os RFs e RNFs críticos estiverem ligados a casos de uso e testes;
- testes de carga, falha, idempotência, replay, backup, restore e rollback estiverem
  planejados e com responsáveis;
- região, retenção, canal de alerta e limiares tiverem decisão registrada;
- a estimativa reproduzível permanecer abaixo de US$ 1.500 por mês;
- segurança e LGPD tiverem revisão formal;
- `mkdocs build --strict` passar no CI.

## 15. Histórico e aprovação

| Versão | Data | Status | Descrição | Autor(es) |
| -- | -- | -- | -- | -- |
| 1.0 | 08/09/2026 | Substituída | Versão inicial. | Joao Vitor Donda, Caique Rechuan e Joao Gabriel Meirelles |
| 1.1 | 17/09/2026 | Em revisão | Alinhamento de SLOs, custo, durabilidade, alertas, LGPD e critérios verificáveis. | Equipe do projeto |

| Papel aprovador | Nome | Data | Decisão |
| -- | -- | -- | -- |
| Arquiteto de Soluções | | | Pendente |
| Responsável de Segurança | | | Pendente |
| Professor responsável | | | Pendente |
