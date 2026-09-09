---
hide:
    - toc
---

# Lavoura Inteligente

**Plataforma de Telemetria Agrícola** — Case 6: AgTech<br>
Disciplina IBM8936 · Turma PC_ADS_26.2_8001_II

Sensores IoT distribuídos por lavouras de grande extensão enviam, a cada minuto,
leituras de umidade do solo, acidez, temperatura e clima. A plataforma recebe essa
telemetria, avalia os limiares críticos de cada cultura e emite alertas de irrigação
aos produtores, além de consolidar os dados para os painéis dos agrônomos de campo.

O projeto reprojeta essa arquitetura sobre serviços gerenciados da AWS, substituindo o
banco relacional — incapaz de sustentar a concorrência de escrita das séries temporais —
por um modelo NoSQL de escrita distribuída, dentro de um orçamento de até
**US$ 1.500,00/mês**.

<div class="module-cards grid four-cols">
    <div class="card module-card">
        <div class="card-header">Iniciação</div>
        <div class="card-content">
            <p class="contributors">Documento de visão, metodologia, pesquisa e protótipo de baixa fidelidade</p>
            <a href="Iniciacao/" class="button primary-btn">Acessar</a>
        </div>
    </div>
    <div class="card module-card">
        <div class="card-header">Elaboração</div>
        <div class="card-content">
            <p class="contributors">Requisitos, casos de uso, diagramas e protótipo de alta fidelidade</p>
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
| Amazon API Gateway | Endpoint HTTPS de entrada da telemetria enviada pelos sensores |
| AWS Lambda (ingestão) | Validação e sanitização dos payloads antes da gravação |
| Amazon DynamoDB | Persistência da telemetria, particionada por sensor e ordenada por tempo |
| DynamoDB Streams + Lambda | Avaliação dos limiares críticos e disparo dos alertas de irrigação |
| Amazon SNS | Entrega dos alertas aos produtores |
| Amazon S3 | Arquivos históricos e consolidados de safras passadas |
| Amazon S3 + CloudFront | Frontend dos painéis, distribuído com HTTPS |
| Amazon CloudWatch | Logs, métricas de ingestão e alarmes de falha das funções Lambda |
