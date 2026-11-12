# Integrações AWS e ambientais

## Escopo implementado

Esta evolução preserva o deploy AP2 em EC2/PostgreSQL e acrescenta serviços reais,
sem converter toda a arquitetura-alvo em uma implantação de produção.

| Componente | Implementação |
| -- | -- |
| INPE/DETER | WFS público Amazônia e Cerrado; consulta pelo envelope do talhão e buffer; snapshots com SHA-256 e hora da consulta |
| Geoprocessamento | Shapely/PROJ: topologia, interseção e distância em projeção métrica local, buffer de 100 m e corte em 31/12/2020 |
| Histórico | Polígono e datasets preservados por análise; alterações de geometria pela API geram evento com antes/depois e hash |
| S3 | Objetos JSON de análises, versões de polígono e auditoria; bucket privado/versionado, criptografia AES256, HTTPS obrigatório |
| DynamoDB | Projeção de status por `PK=TALHAO#id`, `SK=STATUS`, com condição para impedir retry antigo de sobrescrever versão mais recente |
| SNS | Publicação de mudanças de status ambiental em tópico próprio; nenhum destinatário de e-mail/SMS cadastrado automaticamente |
| Outbox | Intenção de entrega salva na mesma transação do domínio; retries não apagam registros; falhas exibidas no Admin |
| Agendamento | Worker do Compose consulta novamente após 24 h e processa a fila AWS a cada minuto; até 100 talhões nesta implantação de demonstração |
| Backup | `backup_db.sh` gera dump e envia ao S3, junto dos arquivos de vistoria, quando o bucket está configurado |
| Segurança | Sessão/CSRF; gravações da API restritas à equipe; função IAM da EC2 limitada ao bucket, tabela e tópico da aplicação; nenhuma chave no código |

O serviço WFS é documentado pelo [INPE/TerraBrasilis](https://terrabrasilis.dpi.inpe.br/download-de-dados/).
O DETER distingue [alertas de desmatamento, degradação e exploração](https://www.gov.br/inpe/pt-br/area-conhecimento/unidade-amazonia/projetos-e-pesquisas/deter/deter).
Somente interseção com classe `DESMATAMENTO*` posterior ao corte produz bloqueio automático.
Proximidade, degradação, erro de consulta, geometria inválida e cobertura incompleta
permanecem em revisão. Ausência de alertas DETER não aprova automaticamente o talhão.
Um bloqueio existente é preservado se a reconsulta falhar ou não o confirmar;
qualquer liberação exige revisão humana com justificativa.

Datas de detecção não comprovam a data exata da supressão. A validade de 24 horas
é prazo interno para nova consulta, não garantia de atualização diária da fonte.
O serviço público pode apresentar defasagem. O sistema classifica risco operacional;
não emite certificação jurídica de conformidade EUDR.

## Infraestrutura como código

O arquivo `infra/aws-integracoes.json` é um template CloudFormation validado no console.
Cria bucket, política HTTPS, tabela DynamoDB sob demanda (limite 10 unidades/s para
leitura e escrita), tópico SNS criptografado e função/perfil IAM para a EC2 existente.
S3 e DynamoDB usam `DeletionPolicy: Retain`: excluir a pilha não elimina as evidências.
Versionamento não equivale a Object Lock ou retenção legal de cinco anos.

A [função IAM da EC2](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_use_switch-role-ec2.html)
fornece credenciais temporárias. Não copie o `.env` ou chaves para o GitHub.
O `.env.example` contém apenas os nomes dos recursos necessários:

```dotenv
AWS_DEFAULT_REGION=us-east-2
RAIZES_S3_BUCKET=raizes-evidencias-CONTA-us-east-2
RAIZES_DYNAMODB_TABLE=raizes-status
RAIZES_SNS_TOPIC_ARN=arn:aws:sns:us-east-2:CONTA:raizes-alertas
```

O perfil da pilha deve ser vinculado à instância. Para containers em bridge, verificar
se IMDSv2 pode ser acessado com o limite de saltos apropriado; manter tokens obrigatórios.
O código usa a cadeia padrão de credenciais do SDK e não persiste tokens temporários.

## Operação e verificação

```bash
cd src
docker compose up -d --build
docker compose exec -T web python manage.py test lavouraInteligente --noinput
docker compose exec -T web python manage.py sincronizar_ambiental --talhao 1
docker compose exec -T web python manage.py sincronizar_ambiental --somente-cloud
docker compose logs --tail 30 integracoes
```

No portal, **Monitoramento ambiental** mostra fontes, análises, motivo, prazo e fila.
`POST /app/talhoes/ID/analisar/` exige equipe/CSRF e limita consultas manuais a uma a
cada cinco minutos por origem. `GET /app/analises/ID/` baixa evidências e GeoJSON.
Requisições concorrentes são coordenadas com advisory locks PostgreSQL; edição do
polígono durante a consulta rejeita o resultado antigo.

Dados DETER brutos são preservados no PostgreSQL e enviados como JSON ao S3.
O hash da resposta original permite identificar sua versão; o JSON persistido é uma
representação normalizada, não a sequência original de bytes da resposta HTTP.
SNS Standard e retries podem duplicar mensagens; consumidores devem deduplicar pela
identificação da análise. A tabela DynamoDB é uma projeção: PostgreSQL continua como
fonte de verdade da balança nesta implantação.

Antes de atualizar, gerar backup e preservar a imagem anterior para rollback. Nunca
executar `docker compose down -v`. Para restaurar, use banco separado e compare
contagens antes de qualquer substituição do banco ativo. A cópia S3 depende de sucesso
do envio; falhas encerram o script com erro e devem ser acompanhadas no log do cron.

## Validação

36 testes aprovados em PostgreSQL 18 isolado no Windows: domínio original, interface,
autenticação/CSRF, uploads, exportações, corte temporal, interseção, distância, fonte
truncada/indisponível, preservação de bloqueio, edição concorrente e retry AWS.
Os testes AWS usam o Stubber oficial do botocore; comprovação dos serviços reais deve
ser registrada separadamente após provisionamento e envio na EC2.

## Limites e evolução

MapBiomas Alerta, Sentinel/NDVI e análise espectral ainda não estão integrados.
As fontes mencionadas em atributos dos dados de seed são exemplos e não ingestões.
Também permanecem pendentes: RDS/PostGIS, Lambda/API Gateway/EventBridge, Athena/Parquet,
Cognito/MFA e autorização por cooperativa; multipart de 5 GB; GeoTIFF georreferenciado
com data e cobertura de 95%; Object Lock/KMS próprio; exclusão lógica e pacote de
retenção integral. O worker Compose substitui apenas o agendamento desta demonstração.
O registro de versões pela API não cobre edições diretas no SQL ou Django Admin.
As metas de 25 mil talhões, RPO/RTO e SLA da arquitetura exigem validação própria.

## Custos

O responsável informou US$90 de créditos e autorizou criar esta pilha em 11/11/2026.
Para poucos usuários, poucos talhões e arquivos pequenos até sábado 14/11, a estimativa
preliminar é US$3–10, incluindo a EC2 atual. Não é teto nem fatura: depende de outras
cargas da conta, elegibilidade dos créditos, tráfego e armazenamento/versionamento.
Não há NAT Gateway, balanceador, RDS ou cluster novo nesta pilha.

Consultar os preços oficiais de [EC2](https://aws.amazon.com/ec2/pricing/on-demand/),
[IPv4/VPC](https://aws.amazon.com/vpc/pricing/), [S3](https://aws.amazon.com/s3/pricing/),
[DynamoDB](https://aws.amazon.com/dynamodb/pricing/) e [SNS](https://aws.amazon.com/sns/pricing/).
O limite de capacidade DynamoDB reduz picos de requisições; não limita a fatura total.

## Registro de implantação

11/11/2026: template validado no console e criação da pilha `raizes-integracoes`
concluída com `CREATE_COMPLETE` em us-east-2. Vinculação IAM, deploy da aplicação e
envios reais devem ser registrados após verificação, abaixo.
