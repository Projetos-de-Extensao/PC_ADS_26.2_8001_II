import uuid
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand,CommandError
from lavouraInteligente.simulacao import CENARIOS,criar

class Command(BaseCommand):
    help='Cria os seis cenários de apresentação uma única vez, sem criar contas ou redefinir dados.'
    def handle(self,*args,**options):
        actor=get_user_model().objects.filter(is_superuser=True,is_active=True).order_by('pk').first()
        if not actor:raise CommandError('Cadastre um administrador antes de preparar os exemplos.')
        for name in CENARIOS:
            key=uuid.uuid5(uuid.NAMESPACE_URL,'raizes:apresentacao:'+name)
            row=criar(name,actor,key)
            self.stdout.write(f'{name}: {row.talhao.codigo} / {row.talhao.status}')
