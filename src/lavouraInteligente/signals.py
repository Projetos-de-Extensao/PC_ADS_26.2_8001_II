"""Cloud status projection and evidence archive follow committed domain changes."""
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Talhao, EventoAuditoria
from .cloud import enqueue

@receiver(post_save,sender=Talhao)
def status_projection(sender,instance,raw=False,**kwargs):
    if raw:return
    simulated=instance.atributos.get('ambiente')=='SIMULACAO'
    key=('DEMO#' if simulated else '')+f'TALHAO#{instance.pk}'
    enqueue('STATUS',key,{'talhao':instance.pk,'codigo':instance.codigo,'simulado':simulated,
        'status':instance.status,'atualizado_em':instance.atualizado_em.isoformat(),
        'analise_ambiental':instance.atributos.get('analise_ambiental')})

@receiver(post_save,sender=EventoAuditoria)
def audit_archive(sender,instance,created,raw=False,**kwargs):
    if raw or not created:return
    from .models import CenarioSimulado,LoteTalhao
    simulated=bool(instance.dados.get('simulado'))
    if instance.recurso=='talhao':simulated=simulated or CenarioSimulado.objects.filter(talhao_id=instance.recurso_id).exists()
    if instance.recurso=='lote':simulated=simulated or LoteTalhao.objects.filter(lote_id=instance.recurso_id,talhao__cenario_simulado__isnull=False).exists()
    prefix='demonstracao/auditoria' if simulated else 'auditoria'
    enqueue('EVIDENCIA',f'{prefix}/evento-{instance.pk}.json',{'id':instance.pk,'ator_id':instance.ator_id,'simulado':simulated,
        'acao':instance.acao,'recurso':instance.recurso,'recurso_id':instance.recurso_id,
        'descricao':instance.descricao,'dados':instance.dados,'criado_em':instance.criado_em.isoformat()})
