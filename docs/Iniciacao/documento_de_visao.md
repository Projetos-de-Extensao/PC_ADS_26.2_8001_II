---
id: documento_de_visao
title: Documento de Visão
---

# Documento de Visão (v2.1)

**Projeto**: Lavoura Inteligente — Rastreabilidade Agrícola e Conformidade EUDR<br>
**Case**: 6 — AgTech<br>
**Turma**: PC_ADS_26.2_8001_II<br>
**Fase**: Iniciação<br>
**Status**: Em revisão

## 1. Introdução

Este documento apresenta o problema de negócio, os usuários, o escopo e as metas de
qualidade da plataforma Lavoura Inteligente. Os detalhes funcionais e os critérios
mensuráveis estão, respectivamente, no Levantamento de Requisitos e no Documento de
Requisitos Suplementares. A arquitetura técnica está descrita no Documento de
Arquitetura.

### 1.1. Propósito

Definir uma visão comum para uma plataforma que consolida dados de produtores, talhões,
fontes ambientais e eventos de recebimento, mantém um **status de risco atualizado** para
cada área e responde, em poucos segundos, se um lote que chega à cooperativa tem origem
rastreável e evidências suficientes para ser aceito.

A pergunta central do produto é:

> **"Este lote tem origem rastreável e evidências suficientes para ser aceito sem gerar
> risco de conformidade?"**

### 1.2. Mudança de escopo em relação à v1

A versão 1 tratava o case como telemetria de sensores IoT (umidade, acidez, temperatura)
com alertas de irrigação. A versão 2 mantém o núcleo técnico pedido pelo Case 6 —
ingestão em escala, escrita distribuída em NoSQL e visualização — mas o aplica a um
problema de negócio mais concreto: rastreabilidade de origem e risco socioambiental,
motivado pela regulamentação europeia EUDR.

### 1.3. Escopo

Estão no escopo:

1. cadastro de produtores, fazendas, talhões e documentos de origem;
2. upload, validação e versionamento dos polígonos dos talhões (KML/GeoJSON);
3. ingestão periódica de fontes ambientais (ex.: MapBiomas Alerta, DETER, camadas
   derivadas do Sentinel);
4. análise espacial entre polígonos e camadas ambientais;
5. cálculo e armazenamento do status de cada talhão: **APROVADO**, **REVISÃO** ou
   **BLOQUEADO**, sempre com motivo e evidências;
6. consulta do status no momento da recepção do lote (balança/romaneio);
7. notificação de mudanças críticas de status;
8. **vistoria por drone**: quando o satélite deixa dúvida, um drone sobrevoa o talhão e
   as imagens viram evidência para a decisão do analista;
9. mapeamento do contorno do talhão a partir do voo do drone, para corrigir polígonos
   enviados com erro;
10. histórico, consulta analítica e geração de pacote auditável;
11. infraestrutura AWS, segurança, observabilidade, backup e CI/CD.

Estão fora do escopo desta fase: parecer jurídico de conformidade, integração com o
sistema oficial da União Europeia para envio de declarações, processamento próprio de
imagens de satélite brutas (usaremos camadas e alertas já processados por fontes
públicas), sensores IoT em campo, controle de voo dos drones e geração do ortomosaico
(feita pelo software do próprio drone, antes do envio à plataforma).

### 1.4. Glossário

- **EUDR**: *European Union Deforestation Regulation*, regulamento europeu sobre produtos
  livres de desmatamento. Abrange gado, cacau, café, óleo de palma, borracha, soja e
  madeira, além de derivados.
- **Data de corte**: 31/12/2020. Áreas desmatadas após essa data não podem originar
  produtos aceitos pela EUDR.
- **Talhão**: menor unidade de área cadastrada, representada por um polígono.
- **Lote/romaneio**: carga recebida pela cooperativa, vinculada a um ou mais talhões.
- **Status**: classificação operacional de risco (APROVADO, REVISÃO, BLOQUEADO). Não é
  certificação jurídica.
- **Evidência**: registro versionado que justifica um status (polígono usado, dataset,
  data, resultado da análise espacial).
- **Hot data / cold data**: dados de consulta frequente e rápida (DynamoDB) versus dados
  históricos e volumosos (S3).
- **PostGIS**: extensão geoespacial do PostgreSQL.
- **Vistoria por drone**: voo sobre um talhão em REVISÃO para obter imagens de alta
  resolução e confirmar, de perto, o que o satélite não conseguiu esclarecer.
- **Ortomosaico**: imagem única e georreferenciada montada a partir das fotos do voo,
  entregue em formato GeoTIFF.
- **SLA/SLO/SLI, RPO/RTO**: acordo, objetivo e indicador de serviço; perda máxima de dados
  e tempo máximo de recuperação.

### 1.5. Referências

- Comissão Europeia — Regulation on Deforestation-free Products (EUDR).
- AWS Well-Architected Framework.
- Lei Geral de Proteção de Dados (Lei nº 13.709/2018).
- Documentação oficial de Amazon DynamoDB, AWS Lambda, Amazon S3, Amazon Athena,
  Amazon EventBridge e PostGIS.
- Plano de Ensino e roteiro do Case 6 — AgTech.

## 2. Posicionamento

### 2.1. Problema e oportunidade

Cooperativas e cerealistas recebem produção de milhares de produtores. Os dados de
origem chegam em planilhas, KMLs, GeoJSONs, e-mails e sistemas diferentes, muitas vezes
com erros de geometria. Verificar manualmente cada origem é lento, difícil de auditar e
inviável no pico da colheita, quando caminhões chegam continuamente à balança.

A EUDR passa a exigir, a partir de **30/12/2026** para grandes e médias empresas e
**30/06/2027** para a maioria das micro e pequenas, que produtos exportados à União
Europeia comprovem origem livre de desmatamento. Isso cria demanda por rastreabilidade
geoespacial, histórico e evidências auditáveis.

> A EUDR é usada neste trabalho como motivação técnica e de negócio, não como
> aconselhamento jurídico.

### 2.2. Ideia-chave da solução

O sistema **pré-processa** as informações complexas antes da chegada do caminhão. Na
balança, a aplicação apenas consulta um status já calculado no DynamoDB, em vez de
executar toda a análise do zero.

O monitoramento acontece em duas camadas:

- **Satélite (todos os talhões, sempre)**: fontes públicas cobrem todas as áreas, mas
  com resolução de cerca de 10 metros e sujeitas a nuvens.
- **Drone (só quando há dúvida)**: quando um talhão cai em REVISÃO, uma vistoria por
  drone gera imagens de alta resolução daquele talhão específico, para o analista
  decidir com segurança.

### 2.3. Posicionamento do produto

Para cooperativas e cerealistas que precisam comprovar a origem da produção, a
**Lavoura Inteligente** é uma plataforma de rastreabilidade que cruza polígonos de
talhões com dados ambientais e entrega uma decisão operacional rastreável em poucos
segundos. Diferentemente da verificação manual, o status é recalculado automaticamente
quando chegam novos dados e toda decisão fica acompanhada de evidências versionadas.

## 3. Stakeholders e usuários

| Perfil | Necessidade primária | Resultado esperado |
| -- | -- | -- |
| Cooperativa / cerealista | Aceitar apenas lotes com origem rastreável. | Menor risco comercial e regulatório. |
| Operador da balança | Saber rapidamente se pode receber o lote. | Resposta APROVADO/REVISÃO/BLOQUEADO com motivo. |
| Analista de conformidade / agrônomo | Investigar talhões em revisão. | Evidências claras e histórico por área. |
| Produtor rural | Cadastrar áreas e entender seu status. | Saber o que corrigir para ser aprovado. |
| Piloto de drone / equipe de campo | Saber quais talhões vistoriar e enviar as imagens. | Vistorias concluídas e aceitas como evidência. |
| Administrador | Manter usuários, cadastros e integrações. | Dados íntegros e acessos controlados. |
| Auditor | Verificar decisões passadas. | Pacote de evidências reproduzível. |
| Fontes ambientais externas | Publicar alertas e camadas. | Dados ingeridos com origem e data registradas. |
| Operação / DevOps | Implantar e observar o serviço. | Operação rastreável dentro dos SLOs e do orçamento. |
| Diretoria / CFO | Controlar o gasto. | Custo total inferior a US$ 1.500 por mês. |
| Corpo docente | Avaliar a solução. | Decisões justificadas e evidências reproduzíveis. |

## 4. Visão da solução

### 4.1. Como o produto funciona para o usuário

1. O produtor ou a cooperativa cadastra fazendas, talhões e documentos de origem.
2. O sistema valida e armazena os polígonos geográficos de cada talhão.
3. Dados externos e alertas ambientais são ingeridos periodicamente.
4. Um motor de processamento cruza os polígonos com as fontes ambientais.
5. O sistema atualiza o status de risco de cada talhão e mantém o histórico das
   evidências.
6. Se o talhão cair em REVISÃO, o analista pode pedir uma vistoria por drone; o piloto
   voa, envia as imagens e o analista decide com base nelas.
7. Quando um lote chega, a aplicação consulta o status pré-calculado e responde em
   poucos segundos.
8. Mudanças críticas geram alertas e ficam registradas para auditoria.

### 4.2. Exemplo de decisão na balança

| Campo | Valor |
| -- | -- |
| Produtor | Fazenda Santa Rita |
| Talhão | TALHAO_8F23 |
| Lote | 2026-09-00128 |
| Status | APROVADO |
| Motivo | Polígono válido, origem rastreável e nenhuma ocorrência crítica ativa nas fontes processadas. |

### 4.3. Arquitetura em uma frase

API Gateway e EventBridge recebem chamadas e eventos; Lambdas processam; DynamoDB guarda
o status operacional; S3 guarda o histórico e as imagens dos drones; Athena consulta o data lake; PostgreSQL com
PostGIS executa as análises geoespaciais; SNS envia alertas; o frontend apresenta mapa,
status e evidências. Detalhes no Documento de Arquitetura.

## 5. Capacidades principais

- cadastro de produtores, fazendas e talhões com polígonos versionados;
- validação de arquivos geoespaciais (formato, sistema de coordenadas e geometria);
- ingestão e versionamento de fontes ambientais;
- análise espacial (interseção, área afetada, distância);
- status de risco por talhão com motivo e evidências;
- consulta rápida na recepção do lote;
- revisão humana de casos duvidosos, apoiada por vistoria com drone;
- mapeamento do contorno do talhão pelo voo do drone;
- notificações de mudança crítica;
- histórico analítico e pacote auditável;
- observabilidade, backup e implantação automatizada.

## 6. Premissas, dependências e restrições

- Cenário de referência: **3.000 produtores** e **25.000 talhões**.
- Picos de movimentação concentrados na colheita; baixo tráfego fora da safra.
- Fontes ambientais públicas com atualização diária (alertas) a mensal/anual (camadas
  de cobertura).
- O status é uma classificação de risco operacional, sempre com revisão humana possível.
- Vistorias por drone são feitas por equipe própria da cooperativa ou terceirizada,
  que segue as regras da ANAC e do DECEA para voo de drones. Cenário de referência:
  até 300 vistorias por safra, com até 5 GB de imagens por voo.
- Stack principal: Python, serverless AWS, PostgreSQL/PostGIS, frontend web (React ou
  similar) e infraestrutura como código.
- Equipe de três integrantes e prazo acadêmico de 20 semanas.
- Orçamento máximo de **US$ 1.500 por mês**.
- Dados pessoais de produtores (nome, documento, contato, localização da propriedade)
  são tratados segundo a LGPD.

## 7. Metas de qualidade

| Atributo | Meta da baseline |
| -- | -- |
| Consulta na balança | p95 da API inferior a 500 ms; resposta ao operador em até 3 s. |
| Atualização de status | Talhões afetados recalculados em até 1 h após a ingestão de um novo dataset. |
| Vistoria por drone | Imagens de até 5 GB recebidas com retomada de envio e validadas em até 15 min. |
| Disponibilidade | 99,9% mensal para a API de consulta de status. |
| Rastreabilidade | 100% dos status possuem motivo, versão do polígono, datasets usados e data do cálculo. |
| Evidências | Evidências preservadas por no mínimo 5 anos, versionadas e protegidas contra alteração. |
| Recuperação | RPO inferior a 15 min e RTO inferior a 4 h. |
| Segurança | TLS 1.2+; criptografia KMS em repouso; MFA e controle por perfil. |
| Custo | Total mensal inferior a US$ 1.500. |

Os métodos de medição e os critérios completos estão no Documento de Requisitos
Suplementares.

## 8. Aprovação e histórico

| Versão | Data | Status | Descrição | Autor(es) |
| -- | -- | -- | -- | -- |
| 1.0 | 08/09/2026 | Substituída | Versão inicial (telemetria IoT). | Joao Vitor Donda, Caique Rechuan e Joao Gabriel Meirelles |
| 1.1 | 17/09/2026 | Substituída | Alinhamento de escopo, atores, fluxos AWS e SLOs (telemetria IoT). | Equipe do projeto |
| 2.0 | 01/10/2026 | Substituída | Mudança de escopo para rastreabilidade agrícola e conformidade EUDR. | Equipe do projeto |
| 2.1 | 01/10/2026 | Em revisão | Inclusão da vistoria e do mapeamento de talhões por drone. | Equipe do projeto |

| Papel aprovador | Nome | Data | Decisão |
| -- | -- | -- | -- |
| Arquiteto de Soluções | | | Pendente |
| Professor responsável | | | Pendente |
