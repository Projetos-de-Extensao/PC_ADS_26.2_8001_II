from django.core.management.base import BaseCommand
from lavouraInteligente.ambiental import analyze
from lavouraInteligente.cloud import flush
from lavouraInteligente.models import Talhao

class Command(BaseCommand):
    help='Consulta INPE/DETER, preserva snapshots e entrega outbox AWS. Sem aprovação automática.'
    def add_arguments(self,parser):
        parser.add_argument('--talhao',type=int)
        parser.add_argument('--limite',type=int,default=100)
        parser.add_argument('--somente-cloud',action='store_true')
    def handle(self,*args,**options):
        if not options['somente_cloud']:
            rows=Talhao.objects.filter(cenario_simulado__isnull=True).order_by('id')
            if options['talhao']:rows=rows.filter(pk=options['talhao'])
            for pk in rows.values_list('id',flat=True)[:options['limite']]:
                try:
                    row=analyze(pk);self.stdout.write(f'Talhão {pk}: {row.status}; análise {row.id}')
                except Exception as exc:self.stderr.write(f'Talhão {pk}: {type(exc).__name__}')
        result=flush();self.stdout.write(str(result))
        if result['falhas']:raise RuntimeError('Há entregas AWS pendentes; consulte a outbox e tente novamente.')
