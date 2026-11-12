import time
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from lavouraInteligente.ambiental import analyze
from lavouraInteligente.cloud import flush
from lavouraInteligente.models import Talhao, AnaliseAmbiental
from django.db import close_old_connections, connection

class Command(BaseCommand):
    help='Worker único: reconsulta ambiental diária e reenvio AWS a cada minuto.'
    def handle(self,*args,**options):
        while True:
            close_old_connections()
            try:
                with connection.cursor() as c:
                    c.execute('SELECT pg_try_advisory_lock(7240,1)');acquired=c.fetchone()[0]
                if acquired:
                    try:
                        for pk in Talhao.objects.order_by('id').values_list('id',flat=True)[:100]:
                            recent=AnaliseAmbiental.objects.filter(talhao_id=pk,criado_em__gte=timezone.now()-timedelta(hours=24)).exists()
                            if not recent:
                                with connection.cursor() as c:
                                    c.execute('SELECT pg_try_advisory_lock(7241,%s)',[pk]);plot_lock=c.fetchone()[0]
                                if plot_lock:
                                    try:analyze(pk)
                                    except Exception as exc:self.stderr.write(f'Análise {pk}: {type(exc).__name__}')
                                    finally:
                                        with connection.cursor() as c:c.execute('SELECT pg_advisory_unlock(7241,%s)',[pk])
                        self.stdout.write(str(flush()))
                    finally:
                        with connection.cursor() as c:c.execute('SELECT pg_advisory_unlock(7240,1)')
            except Exception as exc:self.stderr.write(type(exc).__name__)
            time.sleep(60)
