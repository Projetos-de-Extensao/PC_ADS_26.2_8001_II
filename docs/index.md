---
hide:
    - toc
---

# Raízes

**Rastreabilidade Agrícola e Conformidade EUDR** — Case 6: AgTech<br>
Disciplina IBM8936 · Turma PC_ADS_26.2_8001_II

A **Release 1 da AP2** é uma API Django REST com PostgreSQL 16 (relacional + JSONB e GIN), Gunicorn e Docker Compose em uma EC2 t3.small. Ela cadastra produtores, fazendas, talhões e lotes, filtra atributos JSON e recebe lotes em transação com rollback.

- [API pública](http://18.117.197.72:8000/api/)
- [Django Admin](http://18.117.197.72:8000/admin/)
- [Validação e evidências da AP2](Transicao/validacao_ap2.md)
- [Procedimento de deploy PostgreSQL](Construcao/deploy_ec2_postgres.md)

A proposta local inclui agora o [frontend operacional do Raízes](Construcao/frontend_raizes.md),
com telas próprias de login, painel/mapa, cadastros, balança, revisão de status, vistorias
e histórico. Ele utiliza o mesmo Django e PostgreSQL, com registros persistidos. Ainda
aguarda revisão e autorização de publicação; o ambiente público continua na versão
anterior.

A arquitetura completa de satélite, drones, análise geoespacial, eventos e auditoria é a evolução planejada. Esses serviços não estão implantados na Release 1. A API acadêmica permite acesso sem autenticação; o Admin exige login.

<div class="module-cards grid four-cols">
    <div class="card module-card">
        <div class="card-header">Iniciação</div>
        <div class="card-content">
            <p class="contributors">Documento de visão e escopo do projeto</p>
            <a href="Iniciacao/" class="button primary-btn">Acessar</a>
        </div>
    </div>
    <div class="card module-card">
        <div class="card-header">Elaboração</div>
        <div class="card-content">
            <p class="contributors">Arquitetura, requisitos, casos de uso e modelo de segurança</p>
            <a href="Elaboracao/" class="button primary-btn">Acessar</a>
        </div>
    </div>
    <div class="card module-card">
        <div class="card-header">Construção</div>
        <div class="card-content">
            <p class="contributors">Workflows, GitHub Projects e ambiente de desenvolvimento</p>
            <a href="Construcao/" class="button primary-btn">Acessar</a>
        </div>
    </div>
    <div class="card module-card">
        <div class="card-header">Transição</div>
        <div class="card-content">
            <p class="contributors">Entrega, implantação e encerramento do projeto</p>
            <a href="Transicao/" class="button primary-btn">Acessar</a>
        </div>
    </div>
</div>

## Integrantes

| Nome |
| -- |
| Joao Vitor Donda |
| Caique Rechuan |
| Joao Gabriel Meirelles |

## Arquitetura-alvo na AWS (evolução futura)

| Serviço | Papel |
| -- | -- |
| Amazon API Gateway | Entrada das APIs do dashboard, da balança e das integrações |
| Amazon EventBridge | Agendamento das coletas e distribuição de eventos entre componentes |
| AWS Lambda | Ingestão, validação de polígonos e de imagens de drone, análise espacial e consulta de status |
| Amazon DynamoDB | Status atual e eventos recentes por talhão (consulta rápida na balança) |
| PostgreSQL + PostGIS (RDS) | Polígonos, relacionamentos e operações espaciais |
| Amazon S3 | Data lake: arquivos brutos, histórico, imagens de drone e evidências imutáveis |
| Amazon Athena | Consultas SQL sobre o histórico no S3 |
| Amazon SNS | Notificações de mudança de status |
| Amazon Cognito | Login, MFA e perfis de acesso |
| CloudFront + S3 | Dashboard web com mapa dos talhões |
| CloudWatch + CloudTrail | Métricas, logs, alarmes e auditoria |
