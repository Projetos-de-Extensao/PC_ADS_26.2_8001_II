"""Cloud status projection and evidence archive follow committed domain changes."""
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Talhao, EventoAuditoria
from .cloud import enqueue

@receiver(post_save,sender=Talhao)
def status_projection(sender,instance,raw=False,**kwargs):
    if raw:return
    enqueue('STATUS',f'TALHAO#{instance.pk}',{'talhao':instance.pk,'codigo':instance.codigo,
        'status':instance.status,'atualizado_em':instance.atualizado_em.isoformat(),
        'analise_ambiental':instance.atributos.get('analise_ambiental')})

@receiver(post_save,sender=EventoAuditoria)
def audit_archive(sender,instance,created,raw=False,**kwargs):
    if raw or not created:return
    enqueue('EVIDENCIA',f'auditoria/evento-{instance.pk}.json',{'id':instance.pk,'ator_id':instance.ator_id,
        'acao':instance.acao,'recurso':instance.recurso,'recurso_id':instance.recurso_id,
        'descricao':instance.descricao,'dados':instance.dados,'criado_em':instance.criado_em.isoformat()})
