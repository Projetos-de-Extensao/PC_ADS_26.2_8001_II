---
hide:
    - toc
---

# Lavoura Inteligente

**Rastreabilidade Agrícola e Conformidade EUDR** — Case 6: AgTech<br>
Disciplina IBM8936 · Turma PC_ADS_26.2_8001_II

A Lavoura Inteligente consolida dados de produtores, talhões, fontes ambientais e
eventos de recebimento para manter um **status de risco atualizado** de cada área. Quando
um lote chega à cooperativa, a balança consulta um status já calculado e recebe, em
poucos segundos, uma resposta: **APROVADO**, **REVISÃO** ou **BLOQUEADO** — sempre com
motivo e evidências.

> Pergunta central: *"Este lote tem origem rastreável e evidências suficientes para ser
> aceito sem gerar risco de conformidade?"*

O projeto usa a regulamentação europeia contra desmatamento (EUDR) como motivação de
negócio e uma arquitetura serverless orientada a eventos na AWS, dentro de um orçamento
de até **US$ 1.500,00/mês**.

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

## Arquitetura na AWS

| Serviço | Papel |
| -- | -- |
| Amazon API Gateway | Entrada das APIs do dashboard, da balança e das integrações |
| Amazon EventBridge | Agendamento das coletas e distribuição de eventos entre componentes |
| AWS Lambda | Ingestão, validação de polígonos, análise espacial e consulta de status |
| Amazon DynamoDB | Status atual e eventos recentes por talhão (consulta rápida na balança) |
| PostgreSQL + PostGIS (RDS) | Polígonos, relacionamentos e operações espaciais |
| Amazon S3 | Data lake: arquivos brutos, histórico e evidências imutáveis |
| Amazon Athena | Consultas SQL sobre o histórico no S3 |
| Amazon SNS | Notificações de mudança de status |
| Amazon Cognito | Login, MFA e perfis de acesso |
| CloudFront + S3 | Dashboard web com mapa dos talhões |
| CloudWatch + CloudTrail | Métricas, logs, alarmes e auditoria |
