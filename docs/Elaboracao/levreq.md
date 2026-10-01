---
id: levantamento_requisitos
title: Levantamento de Requisitos
---

# Levantamento de Requisitos Funcionais (v2.1)

**Projeto**: Lavoura Inteligente — Rastreabilidade Agrícola e Conformidade EUDR<br>
**Data**: 01/10/2026<br>
**Status**: Em revisão

## 1. Objetivo

Registrar as capacidades funcionais do produto de forma identificável e testável. Os
atributos de qualidade estão no Documento de Requisitos Suplementares.

## 2. Perfis e permissões

| Perfil | Escopo funcional |
| -- | -- |
| Administrador | Usuários, perfis, integrações e parâmetros das regras de status. |
| Produtor / Cooperativa | Cadastro de fazendas, talhões, polígonos e documentos de origem sob sua responsabilidade. |
| Analista de conformidade | Consulta de talhões, evidências, revisão humana de status e solicitação de vistoria por drone. |
| Piloto de drone | Lista de vistorias pendentes e envio das imagens dos voos. |
| Operador da balança | Registro de lote e consulta de status no momento da recepção. |
| Gestor | Painéis, consultas históricas e relatórios. |
| Auditor | Consulta somente leitura de trilhas, evidências e pacotes auditáveis. |
| Fonte ambiental (sistema) | Fornecimento de alertas e camadas, coletados de forma agendada. |

## 3. Requisitos funcionais

### 3.1. Identidade e acesso

| ID | Requisito | Prioridade | Critério de aceitação |
| -- | -- | -- | -- |
| RF-IDN-01 | O sistema deve autenticar usuários. | Must | Credencial válida inicia sessão; inválida é recusada sem revelar qual campo falhou. |
| RF-IDN-02 | O sistema deve autorizar ações por perfil e escopo (cooperativa/produtor). | Must | Matriz de permissão impede leitura e alteração fora do escopo. |
| RF-IDN-03 | O administrador deve criar, desativar e alterar perfis de usuários. | Must | Mudanças produzem registro de auditoria. |

### 3.2. Cadastro

| ID | Requisito | Prioridade | Critério de aceitação |
| -- | -- | -- | -- |
| RF-CAD-01 | O sistema deve manter produtores, fazendas e talhões. | Must | CRUD valida relacionamentos, unicidade e impede exclusão com referência ativa. |
| RF-CAD-02 | O produtor deve anexar documentos de origem (ex.: CAR, matrícula). | Should | Arquivo armazenado no S3 com hash, autor e data. |

### 3.3. Geometria dos talhões

| ID | Requisito | Prioridade | Critério de aceitação |
| -- | -- | -- | -- |
| RF-GEO-01 | O usuário deve enviar o polígono do talhão em KML ou GeoJSON. | Must | Arquivo aceito até o limite definido; formato não suportado é recusado com mensagem clara. |
| RF-GEO-02 | O sistema deve validar formato, sistema de coordenadas e geometria. | Must | Polígono aberto, auto-interseção, coordenada fora do Brasil ou área implausível geram erro descritivo. |
| RF-GEO-03 | O sistema deve versionar o polígono do talhão. | Must | Alteração cria nova versão; versões anteriores permanecem consultáveis. |
| RF-GEO-04 | O sistema deve guardar o arquivo original e a geometria normalizada. | Must | Original no S3 e geometria em PostGIS com a mesma versão e hash. |

### 3.4. Fontes ambientais

| ID | Requisito | Prioridade | Critério de aceitação |
| -- | -- | -- | -- |
| RF-AMB-01 | O sistema deve coletar periodicamente alertas e camadas ambientais. | Must | Coleta agendada registra execução, volume e resultado. |
| RF-AMB-02 | Cada dataset deve registrar fonte, versão e data de referência. | Must | Toda evidência aponta para o dataset de origem. |
| RF-AMB-03 | A ingestão deve ser idempotente. | Must | O mesmo arquivo (mesmo hash) não é processado duas vezes. |
| RF-AMB-04 | Falha ou atraso de fonte deve ficar visível. | Must | Talhões que dependem de fonte vencida não podem ficar APROVADO. |

### 3.5. Análise de risco e status

| ID | Requisito | Prioridade | Critério de aceitação |
| -- | -- | -- | -- |
| RF-RSK-01 | O sistema deve cruzar o polígono com as camadas ambientais. | Must | Resultado informa interseção, área afetada e distância ao alerta mais próximo. |
| RF-RSK-02 | O sistema deve calcular o status APROVADO, REVISÃO ou BLOQUEADO. | Must | Status segue as regras RN-02 a RN-05 e sempre possui motivo. |
| RF-RSK-03 | O status deve ser gravado no DynamoDB com sua evidência. | Must | Item STATUS contém versão do polígono, datasets, data do cálculo e validade. |
| RF-RSK-04 | Toda mudança de status deve ficar no histórico. | Must | Transições ficam como eventos e no data lake. |
| RF-RSK-05 | O analista deve revisar e alterar status manualmente. | Must | Alteração exige justificativa, registra autor e preserva a evidência original. |

### 3.6. Vistoria por drone

| ID | Requisito | Prioridade | Critério de aceitação |
| -- | -- | -- | -- |
| RF-DRN-01 | O analista deve solicitar vistoria por drone para um talhão em REVISÃO. | Must | Solicitação registra talhão, motivo, prazo e solicitante; equipe de campo é notificada. |
| RF-DRN-02 | O piloto deve ver as vistorias pendentes com o mapa do talhão. | Must | Lista mostra polígono, localização, prazo e situação (SOLICITADA, AGENDADA, RECEBIDA). |
| RF-DRN-03 | O piloto deve enviar o ortomosaico (GeoTIFF) e as fotos do voo. | Must | Envio de até 5 GB com retomada; arquivo fica vinculado à vistoria. |
| RF-DRN-04 | O sistema deve validar a imagem recebida. | Must | Imagem sem georreferência, sem data, fora da janela da vistoria ou cobrindo menos de 95% do talhão é recusada com motivo. |
| RF-DRN-05 | O analista deve ver a imagem sobre o polígono do talhão. | Must | Mapa sobrepõe ortomosaico, polígono e alertas ambientais. |
| RF-DRN-06 | A vistoria aceita deve virar evidência da decisão. | Must | Revisão que usa a vistoria registra o vínculo; imagem entra no pacote auditável. |
| RF-DRN-07 | O sistema deve sugerir o contorno do talhão a partir do voo. | Should | Diferença acima do limite gera sugestão; nova versão do polígono só após confirmação do produtor. |

### 3.7. Recepção de lotes (balança)

| ID | Requisito | Prioridade | Critério de aceitação |
| -- | -- | -- | -- |
| RF-LOT-01 | O operador deve registrar um lote vinculado a um ou mais talhões. | Must | Lote possui número, data, peso e talhões de origem. |
| RF-LOT-02 | O sistema deve retornar o status do lote. | Must | Resposta traz status, motivo, data do cálculo e talhões avaliados. |
| RF-LOT-03 | Lote com vários talhões deve assumir o pior status. | Must | Um talhão BLOQUEADO torna o lote BLOQUEADO. |
| RF-LOT-04 | A decisão tomada na balança deve ser registrada. | Must | Aceite/recusa fica vinculado ao status consultado e ao operador. |

### 3.8. Alertas e notificações

| ID | Requisito | Prioridade | Critério de aceitação |
| -- | -- | -- | -- |
| RF-ALT-01 | Piora de status deve gerar notificação. | Must | APROVADO → REVISÃO/BLOQUEADO publica no SNS para os inscritos. |
| RF-ALT-02 | Melhora ou resolução também deve ser comunicada. | Should | Transição para APROVADO gera notificação de resolução. |
| RF-ALT-03 | Notificações não podem ser duplicadas. | Must | Reprocessar o mesmo evento não gera segunda notificação. |

### 3.9. Histórico, painel e auditoria

| ID | Requisito | Prioridade | Critério de aceitação |
| -- | -- | -- | -- |
| RF-HIS-01 | O dashboard deve mostrar mapa e lista de talhões por status. | Must | Cores verde/amarelo/vermelho; filtro por produtor, município e status. |
| RF-HIS-02 | O gestor deve consultar histórico por período, município ou produtor. | Should | Consulta usa Athena sobre dados particionados no S3. |
| RF-AUD-01 | O auditor deve consultar eventos críticos. | Must | Filtros por ator, recurso, período e correlation ID, sem permitir alteração. |
| RF-AUD-02 | O sistema deve gerar pacote auditável por produtor ou lote. | Must | Pacote contém polígonos versionados, datasets, análises, vistorias por drone, status e decisões. |

## 4. Regras de negócio

| ID | Regra |
| -- | -- |
| RN-01 | O status é uma classificação de risco operacional, não uma certificação jurídica. |
| RN-02 | Interseção com alerta de desmatamento detectado após 31/12/2020 resulta em BLOQUEADO. |
| RN-03 | Alerta dentro da faixa de proximidade (buffer configurável) sem interseção resulta em REVISÃO. |
| RN-04 | Talhão sem polígono válido, com fonte vencida ou com cálculo fora da validade não pode ser APROVADO. |
| RN-05 | Sem nenhuma das condições acima, o talhão é APROVADO. |
| RN-06 | Revisão humana exige justificativa e não apaga a evidência original. |
| RN-07 | Toda análise registra as versões do polígono e dos datasets usados. |
| RN-08 | Um lote assume o pior status entre seus talhões. |
| RN-09 | Exclusão de cadastro é lógica e preserva evidências durante a retenção. |
| RN-10 | Vistoria por drone só é solicitada para talhões em REVISÃO; não substitui o monitoramento por satélite. |
| RN-11 | Imagem sem georreferência, sem data ou que não cubra o talhão não vale como evidência. |
| RN-12 | A vistoria vale para a decisão daquele momento; um novo alerta de satélite posterior reabre a análise. |

## 5. Dependências

- Definição das fontes ambientais e da frequência de coleta.
- Definição da faixa de proximidade (buffer) e da validade do status.
- Política de retenção para evidências e dados pessoais.
- Formato de integração com o sistema da balança.
- Definição da equipe de drones (própria ou terceirizada), do modelo de câmera e do
  formato de entrega do ortomosaico.

## 6. Histórico e aprovação

| Versão | Data | Status | Descrição | Autor(es) |
| -- | -- | -- | -- | -- |
| 1.0 | 17/09/2026 | Substituída | Requisitos de telemetria IoT. | Equipe do projeto |
| 2.0 | 01/10/2026 | Substituída | Requisitos para rastreabilidade e conformidade EUDR. | Equipe do projeto |
| 2.1 | 01/10/2026 | Em revisão | Inclusão da vistoria e do mapeamento de talhões por drone. | Equipe do projeto |

| Papel aprovador | Nome | Data | Decisão |
| -- | -- | -- | -- |
| Representante de negócio | | | Pendente |
| Arquiteto de Soluções | | | Pendente |
| Professor responsável | | | Pendente |
