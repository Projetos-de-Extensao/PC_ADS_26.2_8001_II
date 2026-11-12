import io
import json
import shutil
import tempfile
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import Client, TestCase, override_settings
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from .models import (ArquivoVistoria, DecisaoRecebimento, EventoAuditoria, Lote,
                     RevisaoStatus, Talhao, Vistoria)


class PortalTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed',verbosity=0)
        cls.user=get_user_model().objects.create_user('equipe',password='local-test-only',is_staff=True)
        cls.review=Talhao.objects.get(codigo='TALHAO_10023')
        cls.approved=Talhao.objects.get(codigo='TALHAO_8F23')

    def setUp(self):
        self.client.force_login(self.user)

    def post(self,url,data):
        return self.client.post(url,json.dumps(data),content_type='application/json')

    def test_portal_exige_sessao_e_equipe(self):
        anon=Client()
        self.assertEqual(anon.get('/').status_code,302)
        common=get_user_model().objects.create_user('comum',password='local-test-only')
        anon.force_login(common)
        self.assertEqual(anon.get('/app/estado/').status_code,403)
        response=self.client.get('/')
        self.assertEqual(response.status_code,200)
        self.assertContains(response,'Talhões e mapa')
        self.assertContains(response,'Recepção de lotes')

    def test_estado_retorna_relacoes_reais(self):
        data=self.client.get('/app/estado/').json()
        self.assertEqual(len(data['talhoes']),4)
        self.assertEqual(len(data['fazendas']),3)
        self.assertEqual(data['usuario']['nome'],'equipe')

    def test_revisao_exige_justificativa_e_preserva_evidencia(self):
        url=f'/app/talhoes/{self.review.id}/revisar/'
        self.assertEqual(self.post(url,{'status':'APROVADO','justificativa':''}).status_code,400)
        before=self.review.atributos.copy()
        response=self.post(url,{'status':'APROVADO','justificativa':'Documentação da origem conferida pela equipe.'})
        self.assertEqual(response.status_code,201)
        self.review.refresh_from_db()
        self.assertEqual(self.review.status,'APROVADO')
        record=RevisaoStatus.objects.get()
        self.assertEqual(record.evidencia_original['atributos'],before)
        self.assertEqual(record.status_anterior,'REVISAO')
        self.assertEqual(record.autor,self.user)
        self.assertEqual(EventoAuditoria.objects.get().ator,self.user)

    def test_revisao_nao_aprova_origem_sem_poligono(self):
        self.review.poligono={};self.review.save()
        response=self.post(f'/app/talhoes/{self.review.id}/revisar/',{'status':'APROVADO','justificativa':'Tentativa sem geometria cadastrada.'})
        self.assertEqual(response.status_code,409)
        self.assertEqual(RevisaoStatus.objects.count(),0)

    def test_decisao_da_balanca_e_imutavel_e_tem_operador(self):
        lote=Lote.objects.first()
        url=f'/app/lotes/{lote.id}/decisao/'
        dados={'acao':'ACEITAR','justificativa':'Origem e documentos conferidos na recepção.'}
        self.assertEqual(self.post(url,dados).status_code,201)
        self.assertEqual(self.post(url,dados).status_code,409)
        decisao=DecisaoRecebimento.objects.get()
        self.assertEqual(decisao.operador,self.user)
        self.assertEqual(decisao.status_consultado,lote.status)

    def test_lote_bloqueado_nao_pode_ser_aceito(self):
        lote=Lote.objects.create(codigo='BLOQUEADO-TESTE',peso_total_kg='1',status='BLOQUEADO')
        response=self.post(f'/app/lotes/{lote.id}/decisao/',{'acao':'ACEITAR','justificativa':'Tentativa de aceitar origem bloqueada.'})
        self.assertEqual(response.status_code,409)
        self.assertFalse(DecisaoRecebimento.objects.filter(lote=lote).exists())

    def test_solicitacao_de_vistoria_e_idempotente(self):
        dados={'motivo':'Conferir a cobertura do solo na área com alerta.','prazo':str(timezone.localdate()+timedelta(days=2))}
        self.assertEqual(self.post(f'/app/talhoes/{self.approved.id}/vistoria/',dados).status_code,409)
        url=f'/app/talhoes/{self.review.id}/vistoria/'
        first=self.post(url,dados)
        self.assertEqual(first.status_code,201)
        second=self.post(url,dados)
        self.assertEqual(second.status_code,200)
        self.assertEqual(first.json()['id'],second.json()['id'])
        self.assertEqual(Vistoria.objects.count(),1)

    def test_imagem_preserva_hash_e_download_exige_login(self):
        directory=tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree,directory)
        vistoria=Vistoria.objects.create(talhao=self.review,solicitante=self.user,motivo='Conferir área',prazo=timezone.localdate())
        content=io.BytesIO();Image.new('RGB',(8,8),'green').save(content,format='PNG')
        with override_settings(MEDIA_ROOT=directory):
            response=self.client.post(f'/app/vistorias/{vistoria.id}/arquivo/',{'arquivo':SimpleUploadedFile('voo.png',content.getvalue(),content_type='image/png')})
            self.assertEqual(response.status_code,201,response.content)
            arquivo=ArquivoVistoria.objects.get()
            self.assertEqual(len(arquivo.sha256),64)
            vistoria.refresh_from_db();self.assertEqual(vistoria.status,'RECEBIDA')
            self.assertEqual(Client().get(f'/app/arquivos/{arquivo.id}/').status_code,302)
            download=self.client.get(f'/app/arquivos/{arquivo.id}/')
            self.assertEqual(download.status_code,200)
            self.assertEqual(b''.join(download.streaming_content),content.getvalue())

    def test_imagem_invalida_nao_muda_vistoria(self):
        vistoria=Vistoria.objects.create(talhao=self.review,solicitante=self.user,motivo='Conferir área',prazo=timezone.localdate())
        response=self.client.post(f'/app/vistorias/{vistoria.id}/arquivo/',{'arquivo':SimpleUploadedFile('falso.png',b'nao e uma imagem')})
        self.assertEqual(response.status_code,400)
        vistoria.refresh_from_db();self.assertEqual(vistoria.status,'SOLICITADA')
        self.assertEqual(ArquivoVistoria.objects.count(),0)

    def test_exportacao_contem_registro_e_manifesto(self):
        import zipfile
        response=self.client.get(f'/app/exportar/talhao/{self.review.id}/')
        self.assertEqual(response.status_code,200)
        with zipfile.ZipFile(io.BytesIO(b''.join(response.streaming_content))) as archive:
            self.assertTrue({'registro.json','manifesto.json'}.issubset(archive.namelist()))
            self.assertEqual(json.loads(archive.read('registro.json'))['talhao']['codigo'],self.review.codigo)

    def test_post_protegido_exige_csrf(self):
        strict=Client(enforce_csrf_checks=True);strict.force_login(self.user)
        response=strict.post(f'/app/talhoes/{self.review.id}/revisar/',json.dumps({'status':'APROVADO','justificativa':'Documento validado pela equipe.'}),content_type='application/json')
        self.assertEqual(response.status_code,403)

    def test_geometria_aberta_e_referencia_ativa_sao_recusadas(self):
        dados={'poligono':{'type':'Polygon','coordinates':[[[-47,-16],[-47.1,-16],[-47.1,-16.1],[-47,-16.1]]]}}
        response=self.client.patch(f'/api/talhoes/{self.review.id}/',json.dumps(dados),content_type='application/json')
        self.assertEqual(response.status_code,400)
        response=self.client.delete(f'/api/produtores/{self.review.fazenda.produtor_id}/')
        self.assertEqual(response.status_code,409)
