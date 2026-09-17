---
id: levantamento_requisitos
title: Levantamento de Requisitos
---

# Levantamento de Requisitos Funcionais (v1.0)

**Projeto**: Lavoura Inteligente<br>
**Data**: 17/09/2026<br>
**Status**: Em revisão

## 1. Objetivo

Registrar as capacidades funcionais do produto de forma identificável e testável. Os
atributos de qualidade aplicáveis estão no Documento de Requisitos Suplementares.

## 2. Perfis e permissões

| Perfil | Escopo funcional |
| -- | -- |
| Administrador | Usuários, fazendas, talhões, culturas, sensores, limiares e auditoria. |
| Agrônomo | Consulta de talhões, leituras, alertas e recomendações dentro de suas fazendas. |
| Produtor | Consulta e recebimento de alertas das fazendas sob sua responsabilidade. |
| Gestor | Visão consolidada e relatórios de safra. |
| Auditor | Consulta somente leitura de trilhas e evidências autorizadas. |
| Sensor IoT | Envio autenticado de telemetria apenas para sua própria identidade. |

## 3. Requisitos funcionais

### 3.1. Identidade e administração

| ID | Requisito | Prioridade | Critério funcional de aceitação |
| -- | -- | -- | -- |
| RF-IDN-01 | O sistema deve autenticar usuários. | Must | Credencial válida inicia sessão; inválida é recusada sem revelar qual campo falhou. |
| RF-IDN-02 | O sistema deve autorizar ações por perfil e escopo de fazenda. | Must | Matriz de permissão impede leitura e alteração fora do escopo. |
| RF-IDN-03 | O administrador deve criar, desativar e alterar perfis de usuários. | Must | Mudanças produzem registro de auditoria. |
| RF-ADM-01 | O administrador deve gerenciar fazendas, talhões e culturas. | Must | CRUD valida relacionamentos, unicidade e impedimentos de exclusão. |
| RF-ADM-02 | O administrador deve associar sensores a um talhão. | Must | Sensor ativo pertence a um único talhão por intervalo de vigência. |
| RF-ADM-03 | O administrador deve configurar limiares por cultura/talhão. | Must | Regra possui versão, vigência, autor, unidade, histerese e janela de silêncio. |
| RF-ADM-04 | O sistema deve projetar limiares ativos para o caminho de alertas. | Must | Mudança aprovada no RDS aparece na projeção DynamoDB e é reconciliável. |

### 3.2. Sensores e ingestão

| ID | Requisito | Prioridade | Critério funcional de aceitação |
| -- | -- | -- | -- |
| RF-SEN-01 | O administrador deve provisionar, rotacionar e revogar identidade de sensor. | Must | Operação em um sensor não altera credenciais dos demais e fica auditada. |
| RF-IOT-01 | O sensor deve enviar umidade, acidez, temperatura e clima por HTTPS autenticado. | Must | Payload conforme esquema e sensor ativo seguem para persistência. |
| RF-IOT-02 | O sistema deve validar esquema, unidade, faixa, timestamp e identidade. | Must | Dado inválido recebe 4xx com correlation ID e não é marcado como aceito. |
| RF-IOT-03 | O sistema deve tornar a ingestão idempotente. | Must | Repetição da mesma chave retorna o resultado anterior sem duplicar a leitura. |
| RF-IOT-04 | O sistema deve confirmar sucesso somente após persistência durável. | Must | Falha no DynamoDB retorna 5xx; resposta 2xx implica leitura consultável. |
| RF-IOT-05 | O sistema deve registrar o estado mais recente por sensor e talhão. | Must | Nova leitura válida atualiza a projeção sem regressão por evento atrasado. |

### 3.3. Monitoramento e alertas

| ID | Requisito | Prioridade | Critério funcional de aceitação |
| -- | -- | -- | -- |
| RF-MON-01 | O agrônomo deve consultar o estado atual de um talhão. | Must | Tela informa valor, unidade, sensor, horário e frescor da última leitura. |
| RF-MON-02 | O agrônomo deve consultar histórico por talhão, sensor, tipo e período. | Must | Consulta respeita escopo e pagina resultados ordenados sem Scan integral. |
| RF-ALT-01 | O sistema deve avaliar cada leitura contra a versão vigente do limiar. | Must | Resultado registra leitura, regra e versão usadas. |
| RF-ALT-02 | O sistema deve abrir alerta na transição para estado crítico. | Must | Evento repetido não cria novo alerta dentro da janela configurada. |
| RF-ALT-03 | O sistema deve atualizar severidade e resolver alerta. | Must | Mudanças geram histórico e notificação conforme regra. |
| RF-ALT-04 | O sistema deve publicar alerta nos canais inscritos. | Must | Publicação possui identificador, destinatário, horário e estado de entrega disponível. |
| RF-ALT-05 | Produtor ou agrônomo deve consultar e confirmar ciência de alerta. | Should | Confirmação registra usuário e data, sem encerrar automaticamente a condição. |
| RF-ALT-06 | Ausência de limiar deve gerar pendência operacional. | Must | Leitura permanece armazenada e a pendência identifica cultura/talhão afetado. |

### 3.4. Safras, relatórios e arquivamento

| ID | Requisito | Prioridade | Critério funcional de aceitação |
| -- | -- | -- | -- |
| RF-SAF-01 | O gestor deve abrir e encerrar uma safra. | Must | Período não se sobrepõe indevidamente e encerramento fica auditado. |
| RF-SAF-02 | O gestor deve gerar relatório consolidado da safra. | Must | Relatório informa período, cobertura, agregados, alertas e dados ausentes. |
| RF-ARQ-01 | O sistema deve arquivar telemetria removida da camada quente. | Must | Evento TTL é gravado de forma idempotente no S3 antes de ser considerado arquivado. |
| RF-ARQ-02 | Usuário autorizado deve consultar histórico de safra encerrada. | Should | Consulta usa objetos/derivados do S3 sem degradar a ingestão. |
| RF-ARQ-03 | O sistema deve reconciliar arquivamento. | Must | Processo identifica lacunas, reprocessa falhas e registra evidência de completude. |

### 3.5. Integração meteorológica e auditoria

| ID | Requisito | Prioridade | Critério funcional de aceitação |
| -- | -- | -- | -- |
| RF-MET-01 | O sistema deve complementar leituras com dados meteorológicos externos. | Should | Dado registra fonte e horário; indisponibilidade usa cache e sinaliza desatualização. |
| RF-AUD-01 | Auditor autorizado deve consultar eventos críticos. | Must | Filtros por ator, recurso, período e correlation ID, sem permitir alteração. |

## 4. Regras de negócio

| ID | Regra |
| -- | -- |
| RN-01 | Um sensor ativo possui uma identidade individual e um talhão vigente. |
| RN-02 | Valor sem unidade compatível com o tipo de medição é rejeitado. |
| RN-03 | Uma chave de idempotência identifica uma única leitura do sensor. |
| RN-04 | A regra aplicada é a versão vigente no instante da leitura, registrada na avaliação. |
| RN-05 | Estado crítico só muda segundo limiar, histerese e janela aprovados. |
| RN-06 | Confirmar ciência não resolve a condição agronômica. |
| RN-07 | Exclusão lógica preserva referências e auditoria durante a retenção aplicável. |
| RN-08 | Dados meteorológicos desatualizados não podem ser apresentados como atuais. |

## 5. Dependências

- Definição agronômica dos limiares, unidades, histerese e janela de silêncio.
- Escolha do canal de alerta e do fornecedor de dados meteorológicos.
- Política aprovada de retenção para telemetria, relatórios, auditoria e dados pessoais.

## 6. Histórico e aprovação

| Versão | Data | Status | Descrição | Autor(es) |
| -- | -- | -- | -- | -- |
| 1.0 | 17/09/2026 | Em revisão | Baseline inicial de requisitos funcionais. | Equipe do projeto |

| Papel aprovador | Nome | Data | Decisão |
| -- | -- | -- | -- |
| Representante agronômico | | | Pendente |
| Arquiteto de Soluções | | | Pendente |
| Professor responsável | | | Pendente |
