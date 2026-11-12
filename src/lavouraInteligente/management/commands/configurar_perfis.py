from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from lavouraInteligente.acesso import PERFIS

class Command(BaseCommand):
    help='Cria os grupos funcionais sem criar usuários ou senhas.'
    def handle(self,*args,**options):
        for name in PERFIS:Group.objects.get_or_create(name=name)
        self.stdout.write('Perfis disponíveis. Atribua grupos aos usuários no Admin.')
