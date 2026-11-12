import importlib
import json
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import connection, transaction, IntegrityError
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase
from rest_framework.test import APIClient

from .forms import ProdutorForm
from .models import (Produtor,Fazenda,Talhao,Lote,LoteTalhao,EntregaCloud,DecisaoRecebimento,
                     AnaliseAmbiental,EventoAuditoria)
from .validacao import documento_valido,normalizar_documento,formatar_documento


class IntegridadeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed',verbosity=0)
        cls.user=get_user_model().objects.create_superuser('integridade',password='somente-teste')

    def setUp(self):
        self.api=APIClient();self.api.force_authenticate(self.user)
        self.produtor=Produtor.objects.get(documento='52998224725')
        self.fazenda=Fazenda.objects.first()
        self.talhao=Talhao.objects.first()

    def rejeita(self, model, changes):
        with self.assertRaises(IntegrityError), transaction.atomic():
            model.objects.filter(pk=model.objects.first().pk).update(**changes)

    def test_documentos_dv_numerico_e_alfanumerico(self):
        for value in ['52998224725','11144477735','12345678909','11222333000181','00000000E08G12']:
            with self.subTest(value=value):
                self.assertTrue(documento_valido(value))
                with connection.cursor() as cur:
                    cur.execute('SELECT raizes_documento_valido(%s)',[value])
                    self.assertTrue(cur.fetchone()[0])
        for value in ['11111111111','12345678900','123456789','00000000000000','DEMO-RAIZES','12ABC34501DE00']:
            self.assertFalse(documento_valido(value))
            with connection.cursor() as cur:
                cur.execute('SELECT raizes_documento_valido(%s)',[value]);self.assertFalse(cur.fetchone()[0])

    def test_mascara_e_canonico(self):
        self.assertEqual(normalizar_documento(' 529.982.247-25 '),'52998224725')
        self.assertEqual(normalizar_documento('00.000.000/e08g-12'),'00000000E08G12')
        self.assertEqual(formatar_documento('52998224725'),'529.982.247-25')
        self.assertEqual(formatar_documento('11222333000181'),'11.222.333/0001-81')
        with self.assertRaises(ValidationError):normalizar_documento('529@98224725')

    def test_api_normaliza_cnpj_e_uf(self):
        r=self.api.post('/api/produtores/',{'nome':'Cadastro teste','documento':'00.000.000/e08g-12',
            'municipio':'Cristalina','uf':'go'},format='json')
        self.assertEqual(r.status_code,201,r.data)
        self.assertEqual(r.data['documento'],'00000000E08G12')
        self.assertEqual(r.data['documento_formatado'],'00.000.000/E08G-12')
        self.assertEqual(r.data['uf'],'GO')

    def test_api_rejeita_duplicata_com_mascara(self):
        r=self.api.post('/api/produtores/',{'nome':'Duplicado','documento':'529.982.247-25',
            'municipio':'Cristalina','uf':'GO'},format='json')
        self.assertEqual(r.status_code,400,r.data)
        self.assertIn('documento',r.data)
        r=self.api.patch(f'/api/produtores/{self.produtor.pk}/',{'documento':'529.982.247-25'},format='json')
        self.assertEqual(r.status_code,200,r.data)

    def test_api_rejeita_documento_invalido_e_reserva_demo(self):
        for doc in ['123.456.789-00','123','111.111.111-11','DEMO-RAIZES','529@98224725']:
            r=self.api.post('/api/produtores/',{'nome':'Inválido','documento':doc,'municipio':'A','uf':'GO'},format='json')
            self.assertEqual(r.status_code,400,(doc,r.data))

    def test_api_campos_obrigatorios_uf_e_positivos(self):
        for data in [{'nome':'   '},{'municipio':'\t'},{'uf':'XX'}]:
            r=self.api.patch(f'/api/produtores/{self.produtor.pk}/',data,format='json')
            self.assertEqual(r.status_code,400,(data,r.data))
        for url, data in [(f'/api/fazendas/{self.fazenda.pk}/',{'area_ha':'0'}),
                (f'/api/talhoes/{self.talhao.pk}/',{'area_ha':'-1'}),
                (f'/api/lotes/{Lote.objects.first().pk}/',{'peso_total_kg':'0'})]:
            r=self.api.patch(url,data,format='json');self.assertEqual(r.status_code,400,r.data)

    def test_banco_rejeita_documentos_sem_validadores(self):
        for value in ['529.982.247-25','11111111111','12345678900','111','00000000E08G13']:
            self.rejeita(Produtor,{'documento':value})
        self.rejeita(Produtor,{'documento':'DEMO-RAIZES','simulado':False})
        self.rejeita(Produtor,{'simulado':True})

    def test_banco_rejeita_uf_e_texto_em_branco(self):
        for model,data in [(Produtor,{'uf':'XX'}),(Produtor,{'nome':' \t\n'}),
                (Fazenda,{'municipio':' '}),(Fazenda,{'uf':'go'}),
                (Talhao,{'codigo':' '}),(Talhao,{'cultura':' '}),(Lote,{'codigo':''})]:
            with self.subTest(model=model.__name__,data=data):self.rejeita(model,data)

    def test_banco_rejeita_area_peso_zero_negativo_nan(self):
        for model,field in [(Fazenda,'area_ha'),(Talhao,'area_ha'),(Lote,'peso_total_kg'),(LoteTalhao,'peso_kg')]:
            for value in [Decimal('0'),Decimal('-0.01')]:
                with self.subTest(model=model.__name__,value=value):self.rejeita(model,{field:value})
            with self.assertRaises(IntegrityError), transaction.atomic():
                with connection.cursor() as cur:
                    cur.execute(f'UPDATE {connection.ops.quote_name(model._meta.db_table)} '
                        f'SET {connection.ops.quote_name(field)}=%s WHERE id=%s',
                        ['NaN',model.objects.first().pk])

    def test_banco_rejeita_status_e_json_escalares(self):
        for model,data in [(Talhao,{'status':'INVALIDO'}),(Lote,{'status':'INVALIDO'}),
                (Talhao,{'atributos':[]}),(Talhao,{'poligono':None}),(Talhao,{'poligono':'abc'})]:
            with self.subTest(data=data):self.rejeita(model,data)

    def test_banco_preserva_unique_fk_not_null(self):
        self.rejeita(Produtor,{'nome':None})
        self.rejeita(Talhao,{'codigo':Talhao.objects.last().codigo})
        with self.assertRaises(IntegrityError), transaction.atomic():
            with connection.cursor() as cur:
                cur.execute('UPDATE "lavouraInteligente_fazenda" SET produtor_id=99999999 WHERE id=%s',[self.fazenda.pk])
                cur.execute('SET CONSTRAINTS ALL IMMEDIATE')

    def test_admin_valida_e_normaliza_documento(self):
        form=ProdutorForm(data={'nome':'Teste','documento':'111.444.777-35','municipio':'A','uf':'SP'})
        self.assertTrue(form.is_valid(),form.errors)
        self.assertEqual(form.save().documento,'11144477735')
        form=ProdutorForm(data={'nome':'Teste','documento':'123.456.789-00','municipio':'A','uf':'SP'})
        self.assertFalse(form.is_valid())

    def test_checks_instalados_e_indice_gin(self):
        with connection.cursor() as cur:
            cur.execute("SELECT count(*) FROM pg_constraint WHERE contype='c' AND conrelid IN "
                "(SELECT oid FROM pg_class WHERE relname LIKE 'lavouraInteligente_%')")
            self.assertGreaterEqual(cur.fetchone()[0],53)
            cur.execute("SELECT indexdef FROM pg_indexes WHERE indexname='talhao_atributos_gin'")
            self.assertIn('USING gin',cur.fetchone()[0])

    def test_banco_nao_aceita_origem_bloqueada(self):
        with self.assertRaises(IntegrityError),transaction.atomic():
            DecisaoRecebimento.objects.create(lote=Lote.objects.first(),acao='ACEITAR',
                status_consultado='BLOQUEADO',justificativa='Não deve aceitar.')

    def test_eventos_tem_dominio_e_objeto(self):
        row=EntregaCloud.objects.create(tipo='EVIDENCIA',chave='teste.json',conteudo={})
        self.rejeita(EntregaCloud,{'tipo':'DESCONHECIDO'})
        self.rejeita(EntregaCloud,{'conteudo':[]})

    def test_api_rejeita_poligono_auto_intersectante(self):
        bowtie={'type':'Polygon','coordinates':[[[-47,-16],[-46,-15],[-47,-15],[-46,-16],[-47,-16]]]}
        r=self.api.patch(f'/api/talhoes/{self.talhao.pk}/',{'poligono':bowtie},format='json')
        self.assertEqual(r.status_code,400,r.data)
        self.assertIn('poligono',r.data)

    def test_decisao_revalida_soma_apos_crud(self):
        from .simulacao import criar
        run=criar('livre',self.user)
        lot=Lote.objects.create(codigo='SOMA-DIVERGENTE',peso_total_kg=100,status='APROVADO')
        LoteTalhao.objects.create(lote=lot,talhao=run.talhao,peso_kg=99)
        self.client.force_login(self.user)
        response=self.client.post(f'/app/lotes/{lot.pk}/decisao/',json.dumps({
            'acao':'ACEITAR','justificativa':'Conferência de integridade do recebimento.'}),content_type='application/json')
        self.assertEqual(response.status_code,409,response.content)
        self.assertFalse(DecisaoRecebimento.objects.filter(lote=lot).exists())


class MigracaoDocumentosTests(TransactionTestCase):
    def test_migracao_preserva_vinculos_e_aborta_documento_desconhecido(self):
        old=[('lavouraInteligente','0004_cenariosimulado_uploadsimulado')]
        latest=[('lavouraInteligente','0006_integridade_dominio')]
        executor=MigrationExecutor(connection);executor.migrate(old)
        apps=executor.loader.project_state(old).apps
        Producer=apps.get_model('lavouraInteligente','Produtor')
        Farm=apps.get_model('lavouraInteligente','Fazenda')
        p=Producer.objects.create(nome='João Pereira',documento='123.456.789-00',municipio='A',uf='GO')
        farm=Farm.objects.create(produtor=p,nome='Teste',municipio='A',uf='GO',area_ha=10)
        invalid=Producer.objects.create(nome='Outro',documento='123',municipio='B',uf='SP')
        try:
            with self.assertRaisesRegex(RuntimeError,'IDs de produtores'):
                MigrationExecutor(connection).migrate(latest)
            invalid.documento='111.444.777-35';invalid.save()
            MigrationExecutor(connection).migrate(latest)
            self.assertEqual(Produtor.objects.get(pk=p.pk).documento,'52998224725')
            self.assertEqual(Fazenda.objects.get(pk=farm.pk).produtor_id,p.pk)
            self.assertEqual(Produtor.objects.get(pk=invalid.pk).documento,'11144477735')
        finally:
            Producer.objects.filter(documento='123').delete()
            MigrationExecutor(connection).migrate(latest)
