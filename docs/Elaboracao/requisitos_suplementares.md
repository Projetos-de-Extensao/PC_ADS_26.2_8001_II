---
id: requisitos_suplementares
title: Requisitos Suplementares
---

# Documento de Requisitos Suplementares (v2.1)

**Projeto**: Lavoura Inteligente — Rastreabilidade Agrícola e Conformidade EUDR<br>
**Fase**: Elaboração<br>
**Data**: 01/10/2026<br>
**Status**: Em revisão

## 1. Propósito e escopo

Este documento define requisitos não funcionais, SLOs, regras operacionais e critérios
de aceitação. Os requisitos funcionais estão no Levantamento de Requisitos e ligados aos
casos de uso pela matriz de rastreabilidade.

## 2. Cenário de referência

| Item | Valor adotado para dimensionamento e teste |
| -- | -- |
| Produtores | 3.000 |
| Talhões | 25.000 (média de ~8 por produtor) |
| Polígono | Até 2.000 vértices; arquivo de até 10 MB |
| Fontes ambientais | Alertas diários (ex.: DETER) e camadas mensais/anuais (ex.: MapBiomas) |
| Consultas na balança | Até 5.000 por dia na colheita; pico de 20 por segundo |
| Vistorias por drone | Até 300 por safra; até 5 GB de imagens por voo |
| Crescimento | Até 2x o número de talhões sem mudança estrutural |
| Região | Definida no Documento de Arquitetura antes dos testes |
| Equipe | Três integrantes |
| Orçamento | Até US$ 1.500 por mês |

Testes com valores diferentes devem registrar volume, duração, concorrência e região
para continuar reproduzíveis.

## 3. Definições de medição

- **Consulta de status**: tempo entre a entrada no API Gateway e a resposta com o status
  lido do DynamoDB.
- **Atualização de status**: tempo entre o fim da ingestão de um dataset e a gravação dos
  novos status de todos os talhões afetados.
- **Disponibilidade**: proporção de sondas HTTPS externas, a cada minuto, que recebem a
  resposta esperada dentro do limite de tempo.
- **p95**: valor abaixo do qual ficam 95% das medições válidas.
- **RPO/RTO**: perda máxima de dados e tempo máximo de recuperação.

## 4. Desempenho e capacidade

| ID | Requisito | Critério de aceitação |
| -- | -- | -- |
| RNF-PER-01 | A consulta na balança deve ser rápida. | p95 da API inferior a 500 ms; resposta exibida ao operador em até 3 s. |
| RNF-PER-02 | O status deve refletir novos dados ambientais. | Talhões afetados recalculados em até 1 h após a ingestão do dataset. |
| RNF-PER-03 | A validação de polígono deve ser ágil. | Arquivo de até 10 MB validado em até 30 s. |
| RNF-PER-04 | O dashboard deve abrir rapidamente. | Mapa e lista visíveis em até 3 s para um produtor com até 100 talhões. |
| RNF-PER-05 | Consultas históricas devem ter custo controlado. | Consulta típica no Athena varre menos de 1 GB graças a partições e Parquet. |
| RNF-PER-06 | O envio de imagens de drone deve funcionar com internet de campo. | Upload de até 5 GB em partes, retomando de onde parou após queda de conexão. |
| RNF-PER-07 | A vistoria recebida deve ser validada rapidamente. | Validação de georreferência e cobertura em até 15 min após o fim do upload. |
| RNF-PER-08 | O analista deve ver a imagem do drone sem baixar o arquivo inteiro. | Ortomosaico em COG exibido no mapa em até 5 s. |
| RNF-CAP-01 | A solução deve absorver crescimento. | 2x talhões sem mudança estrutural e sem violar os SLOs. |
| RNF-CAP-02 | O pico da colheita não pode degradar a balança. | 20 consultas/s sustentadas por 30 min sem throttling nem erro acima de 1%. |
| RNF-CAP-03 | Consultas operacionais não podem usar Scan. | Evidência mostra Query por chave ou índice no DynamoDB. |
| RNF-CAP-04 | A modelagem deve evitar hot partition. | Teste de carga sem throttling por partição; plano de sharding documentado. |

## 5. Disponibilidade, durabilidade e recuperação

| ID | Requisito | Critério de aceitação |
| -- | -- | -- |
| RNF-CON-01 | A API de consulta de status deve estar disponível. | 99,9% ao mês (~43 min de indisponibilidade em 30 dias). |
| RNF-CON-02 | A balança deve ter contingência. | Procedimento manual documentado; decisões são registradas no sistema quando ele voltar. |
| RNF-CON-03 | Dados relacionais e geoespaciais devem ter RPO inferior a 15 min. | Backup automático com PITR do RDS testado. |
| RNF-CON-04 | O serviço deve ter RTO inferior a 4 h. | Ambiente reconstruído por IaC e restaurado em exercício. |
| RNF-CON-05 | Evidências não podem ser perdidas nem alteradas. | S3 com versionamento e Object Lock; retenção mínima de 5 anos. |
| RNF-CON-06 | Processamento de eventos deve ser recuperável. | Lambdas com retry, destino de falha (DLQ) e procedimento de reprocessamento. |
| RNF-CON-07 | Reprocessamento não pode duplicar efeitos. | Mesma chave de evento não gera segundo status, evidência ou notificação. |

## 6. Segurança e privacidade

| ID | Requisito | Critério de aceitação |
| -- | -- | -- |
| RNF-SEG-01 | Comunicações devem ser protegidas. | Somente HTTPS com TLS 1.2 ou superior. |
| RNF-SEG-02 | Dados em repouso devem ser criptografados. | RDS, DynamoDB, S3 e logs usam chaves AWS KMS. |
| RNF-SEG-03 | Acesso de usuários deve exigir autenticação forte. | MFA obrigatório para Administrador, Analista e Auditor; perfis por grupo. |
| RNF-SEG-04 | Serviços devem seguir menor privilégio. | Role IAM específica por Lambda, sem curinga amplo sem justificativa. |
| RNF-SEG-05 | Segredos não podem estar em código ou logs. | Credenciais no Secrets Manager; varredura do repositório sem segredos. |
| RNF-SEG-06 | Ações críticas devem ser auditáveis. | Login, revisão de status, alteração de polígono, permissão e decisão na balança registram autor, data e correlação. |
| RNF-SEG-07 | O tratamento deve observar a LGPD. | Inventário de dados pessoais, finalidade, base legal, minimização e retenção documentados. |
| RNF-SEG-08 | Evidências devem ter integridade verificável. | Hash SHA-256 de cada arquivo e evidência, conferido na geração do pacote auditável. |
| RNF-SEG-09 | A integração da balança deve ser autenticada. | Credencial própria por cooperativa, revogável e com limite de requisições. |
| RNF-SEG-10 | Imagens de drone devem ter acesso restrito. | Upload só por link temporário (expira em até 1 h) e apenas para a vistoria atribuída; visualização só por Analista e Auditor; imagens tratadas no inventário LGPD. |

## 7. Operação e observabilidade

| ID | Requisito | Critério de aceitação |
| -- | -- | -- |
| RNF-OPS-01 | A saúde deve ser observável. | Dashboard com disponibilidade, p95, erros, idade dos datasets, fila de falhas e custo. |
| RNF-OPS-02 | Incidentes devem gerar alertas acionáveis. | Alarmes com limiar, responsável, severidade e runbook. |
| RNF-OPS-03 | Logs devem ser correlacionáveis. | 100% das requisições possuem correlation ID e retenção definida. |
| RNF-OPS-04 | Backups devem ser automatizados. | RDS com PITR e retenção de 30 dias; DynamoDB com PITR; S3 versionado. |
| RNF-OPS-05 | Recuperação deve ser praticada. | Restore testado ao menos uma vez por ciclo de entrega. |
| RNF-OPS-06 | Fontes atrasadas devem ser detectadas. | Alarme quando um dataset passa da data esperada de atualização. |

## 8. Manutenibilidade e entrega

| ID | Requisito | Critério de aceitação |
| -- | -- | -- |
| RNF-MAN-01 | Deploy deve ser automatizado. | Pipeline valida e publica versão aprovada em até 10 min. |
| RNF-MAN-02 | Rollback deve ser rápido. | Versão estável restaurada em até 5 min após a decisão. |
| RNF-MAN-03 | Mudanças devem ser rastreáveis. | Deploy registra commit, autor, testes e resultado. |
| RNF-MAN-04 | Operação deve ter runbooks. | Deploy, rollback, incidente, reprocessamento, backup e restore documentados. |
| RNF-MAN-05 | Infraestrutura deve ser reproduzível. | Componentes críticos recriados por IaC versionada. |
| RNF-MAN-06 | Regras de status devem ser parametrizáveis. | Buffer, validade e data de corte configuráveis e versionados, sem novo deploy de código. |
| RNF-MAN-07 | Documentação deve ser publicável. | `mkdocs build --strict` passa no CI antes do deploy. |

## 9. Usabilidade e API

| ID | Requisito | Critério de aceitação |
| -- | -- | -- |
| RNF-USA-01 | O operador deve entender a decisão de imediato. | Tela da balança mostra status com cor, motivo em linguagem simples e data do cálculo. |
| RNF-USA-02 | Erros de geometria devem orientar a correção. | Mensagem indica o problema (ex.: polígono aberto) e, quando possível, o ponto. |
| RNF-USA-03 | A API deve ser documentada. | OpenAPI atualizada e validada no CI. |
| RNF-USA-04 | Respostas devem ser consistentes. | Código HTTP correto, correlation ID e mensagem segura. |

## 10. Custo

| ID | Requisito | Critério de aceitação |
| -- | -- | -- |
| RNF-CUS-01 | O custo total deve respeitar o orçamento. | Estimativa e faturamento abaixo de US$ 1.500/mês. |
| RNF-CUS-02 | O custo deve ser acompanhado. | AWS Budgets alerta em 80%, 90% e 100%. |
| RNF-CUS-03 | Dados frios não podem ficar na camada cara. | Histórico em S3/Parquet com lifecycle; DynamoDB apenas com dados operacionais. |
| RNF-CUS-04 | A estimativa deve ser reproduzível. | Pricing Calculator registra região, volumes, retenção e data dos preços. |
| RNF-CUS-05 | Evitar custos fixos desnecessários. | Sem cluster analítico permanente; VPC Endpoints em vez de NAT Gateway quando possível. |
| RNF-CUS-06 | Imagens de drone não podem inflar o custo de armazenamento. | Drone só para talhões em REVISÃO; imagens vão para S3 Glacier Instant Retrieval 90 dias após a decisão. |

## 11. Responsabilidades

| Responsável | Obrigações principais |
| -- | -- |
| AWS | Serviços gerenciados e infraestrutura física segundo os SLAs de cada serviço. |
| Equipe Lavoura Inteligente | Código, configuração, IAM, dados, testes, custos, backup e resposta a incidentes. |
| Cooperativa | Qualidade dos cadastros, decisão final na balança e revisão humana. |
| Fontes ambientais | Publicação dos dados; a plataforma não garante sua exatidão. |
| Equipe de drones | Voar dentro das regras da ANAC e do DECEA, gerar o ortomosaico e enviar no prazo. |

## 12. Decisões pendentes

| Item | Tratamento antes da aprovação |
| -- | -- |
| Região AWS | Registrar no Documento de Arquitetura e repetir nos testes e custos. |
| Fontes ambientais | Definir quais fontes, formato, frequência e licença de uso. |
| Buffer e validade | Definir faixa de proximidade e validade do status. |
| Retenção | Confirmar retenção de evidências (mínimo 5 anos) e de dados pessoais. |
| Integração da balança | Definir formato de chamada e credenciais. |
| Operação de drones | Definir equipe (própria ou terceirizada), câmera, prazo de vistoria e formato do ortomosaico. |
| Estimativa de custo | Validar no AWS Pricing Calculator. |

## 13. Histórico e aprovação

| Versão | Data | Status | Descrição | Autor(es) |
| -- | -- | -- | -- | -- |
| 1.0 | 08/09/2026 | Substituída | Versão inicial (telemetria IoT). | Joao Vitor Donda, Caique Rechuan e Joao Gabriel Meirelles |
| 1.1 | 17/09/2026 | Substituída | SLOs, custo, durabilidade e LGPD (telemetria IoT). | Equipe do projeto |
| 2.0 | 01/10/2026 | Substituída | Requisitos para rastreabilidade e conformidade EUDR. | Equipe do projeto |
| 2.1 | 01/10/2026 | Em revisão | Inclusão da vistoria e do mapeamento de talhões por drone. | Equipe do projeto |

| Papel aprovador | Nome | Data | Decisão |
| -- | -- | -- | -- |
| Arquiteto de Soluções | | | Pendente |
| Responsável de Segurança | | | Pendente |
| Professor responsável | | | Pendente |
