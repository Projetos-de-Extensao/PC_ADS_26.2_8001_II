# Auditoria completa do roteiro AP2

**Data:** 12/11/2026, America/Sao_Paulo. Fonte: [roteiro oficial do professor](https://jonh-carvalho.github.io/PC_ADS_26.2_8001/Avalia/ap2/), consultado nesta data.
**Prazo indicado:** 12/11/2026, às 20h20. Esta revisão técnica não atribui nota nem registra
aprovação do professor ou participação em apresentação.

## Parte A — Aplicação

| Item | Verificação | Evidência |
| -- | -- | -- |
| A1 | Atendido: produto Raízes, app `lavouraInteligente`, projeto `raizes_config` | Código, Admin e portal no tema AgTech |
| A2 | Atendido: cinco entidades centrais e entidades de apoio; FKs e M:N com peso | `models.py`, migrations, `RelacionalTests` |
| A3 | Atendido: JSONB em atributos/polígono e GIN por migration | Consulta de catálogo PostgreSQL e `DocumentoJsonbTests` |
| A4 | Atendido: recebimento grava lote e itens em `transaction.atomic`; erro desfaz tudo | `TransacaoTests`, testes de peso divergente e talhão repetido |
| A5 | Atendido nos cinco recursos de cadastro: CRUD, aninhamento e filtro JSON | `CrudCompletoTests`, script `validar_api_publica.py`; registros de auditoria são preservados, sem CRUD destrutivo |
| A6 | Atendido: Admin com superusuário existente e estáticos | `AdminSeedTests` e evidência de login/Admin |
| A7 | Atendido: ambiente para banco, SECRET_KEY, DEBUG e hosts | Configuração inspecionada sem revelar segredos; DEBUG=False |
| A8 | Atendido: seed idempotente e 80 testes | Suíte PostgreSQL; [log local](../assets/evidencias/23-integridade-testes-windows.log) |

As [constraints e máscaras](../Construcao/integridade_validacoes.md) são um reforço de
integridade do projeto. O roteiro oficial lista A1–A8; ele não determina um campo
obrigatório `char(11)` nem enumera uma lista própria de CHECKs de CPF.

## Parte B — Deploy

| Item | Verificação | Evidência |
| -- | -- | -- |
| B1 | Atendido quanto ao SO, ferramentas e portas: Amazon Linux 2023, Docker, Compose e Git; SG somente TCP 22 e 8000 | Console AWS + [log de infraestrutura](../assets/evidencias/24-auditoria-infra-ec2.log) |
| B2 | Atendido: `web`, `db`, worker `integracoes`, volume `pgdata`, healthcheck/depends_on | `src/Dockerfile`, `src/docker-compose.yml`, `docker compose ps` |
| B3 | Atendido: `psycopg[binary]`, PostgreSQL configurado pelo ambiente | requirements/settings e engine real `django.db.backends.postgresql` |
| B4 | Atendido: `.env` ignorado; `.env.example` rastreado; sem envio do `.env` | `git ls-files`, `.gitignore`, `.dockerignore`; permissão do arquivo privado |
| B5 | Atendido pelo fluxo Windows → push → pull EC2 → build → bootstrap | Histórico Git, workflow, logs de atualização; `migrate` e `collectstatic` no bootstrap |
| B6 | Atendido: API e Admin pelo IP público | [API](http://18.117.197.72:8000/api/), [Admin](http://18.117.197.72:8000/admin/) |
| B7 | Evidência de down/up sem remover volume já registrada; atualização atual preserva IDs e vínculos | [Persistência](../assets/evidencias/06-persistencia.png), contagens antes/depois |
| B8 | README possui imagens de containers, logs, API, SQL e persistência, identificadas pela origem | [Validação e evidências](validacao_ap2.md); logs atuais complementam capturas históricas |

Console em 12/11: instância `AP2` / `i-0c52ff121375a0404`, t3.small, executando com
3/3 verificações, IP `18.117.197.72`, grupo `launch-wizard-2` / `sg-0581eb4f87348ad80`.
Regras observadas: TCP 8000 e TCP 22, ambas IPv4 `0.0.0.0/0`; nenhuma regra 5432.
O Compose também não publica a porta do banco. Restringir a origem SSH ao IP da equipe
é uma melhoria de segurança recomendada; a regra atual não é descrita como restrita.
Nenhum Elastic IP foi observado. Não foi criada nova infraestrutura nesta revisão.

## Parte C — Documentação

| Artefato | Conferência de conteúdo |
| -- | -- |
| `Iniciacao/dv.md` | Problema, partes interessadas, necessidades, funcionalidades e restrições |
| `Iniciacao/rs.md` | Desempenho, disponibilidade, segurança, operação, custos, SLA e riscos; EC2/Compose/PostgreSQL explícitos |
| `Elaboracao/cua.md` | Casos de uso e cenários arquiteturais com diagramas |
| `Elaboracao/maps.md` | Pacotes/subsistemas, dependências, matriz; arquitetura-alvo diferenciada do protótipo |
| `Elaboracao/dim_comp.md` | t3.small, CPU/RAM, classes e PlantUML; 3 containers, 2 workers web, amostra de memória atual |
| `Elaboracao/dimrbd.md` | Volumetria, crescimento, cálculo, armazenamento, backup/restore e volume EC2 versus RDS |
| `Elaboracao/seq_com.md` | Recebimento, filtro JSONB e deploy; matriz requisito → caso de uso → componente → teste |
| Índices das fases | Links dos artefatos presentes |
| `Transicao/ativ_deploy.md` | Estratégias comparadas, escolha, atividades, estimativa e rollback |
| Publicação/diagramas | Build MkDocs estrito, fontes/SVG locais de Mermaid e PlantUML e workflows de publicação |
| Histórico/aprovações | Histórico técnico registrado. Aprovações humanas permanecem explicitamente pendentes |

As estimativas distinguem disco efetivo de 8 GiB da recomendação de 30 GB. Serviços
S3/DynamoDB/SNS geram custo variável, sem garantia de consumo máximo. O backup recorrente
permanece local; houve apenas uma cópia S3 autorizada. Referências históricas de testes
e capturas são identificadas como históricas, sem substituir a revisão atual.

## Repositório e apresentação

Consulta específica da API GitHub confirmou **`jonh-carvalho` com permissão admin**.
Os três integrantes constam como colaboradores (`jmeirelles02`, `Joaovdonda`, `Rechuanz`)
e os três logins aparecem associados a commits existentes. Não foram fabricados autores
ou commits em nome de outro integrante. O responsável ainda deve confirmar a presença
e a fala de cada integrante no laboratório.

As aprovações dos documentos continuam como pendentes porque não houve decisão humana
registrada. Uma validação automatizada não autoriza marcar a aprovação do professor.

## Extras — sem presumir pontuação

| Extra do roteiro | Estado |
| -- | -- |
| Gunicorn | Implementado e em execução |
| Script de deploy/backup | Implementado e documentado; backup S3 recorrente desativado por escolha do responsável |
| Nginx/HTTPS | Não implantado; demonstração atual em HTTP :8000 |
| Elastic IP | Não associado |
| Objetos com MinIO/S3 + `django-storages` | S3 JSON/evidências existe via boto3, mas `django-storages` não está instalado: não declarar esse bônus automaticamente |
| pgvector / Apache AGE | Não implementados; opcionais |

O laboratório acadêmico exercita drones e fontes sintéticas. Isso não significa que
Cognito, RDS/PostGIS, Athena, Lambda ou arquivos reais de 5 GB estejam implantados.
