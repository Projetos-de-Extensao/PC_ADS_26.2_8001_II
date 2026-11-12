import copy
import hashlib
import json
import os
from unittest.mock import patch

import boto3
from botocore.stub import Stubber, ANY
from django.core.management import call_command
from django.test import TestCase

from .ambiental import analyze, canonical, evaluate, fetch_layer, geometry
from .cloud import deliver, flush
from .models import AnaliseAmbiental, EntregaCloud, Talhao


def polygon(x=-55,y=-10,size=.001):
    return {'type':'Polygon','coordinates':[[[x,y],[x+size,y],[x+size,y+size],[x,y+size],[x,y]]]}

def dataset(geom=None,day='2024-03-01',category='DESMATAMENTO_CR'):
    return {'type':'FeatureCollection','features':[{'id':'test.1','geometry':geom or polygon(),
        'properties':{'view_date':day,'classname':category}}]}


class SpatialTests(TestCase):
    def test_intersecao_pos_corte_bloqueia_e_calcula_area_metrica(self):
        result=evaluate(polygon(),{'AMAZONIA':dataset()})
        self.assertEqual(result['status'],'BLOQUEADO')
        self.assertGreater(result['alertas'][0]['area_intersecao_m2'],10000)

    def test_alerta_anterior_ao_corte_nao_bloqueia_nem_certifica(self):
        result=evaluate(polygon(),{'AMAZONIA':dataset(day='2020-12-31')})
        self.assertEqual(result['status'],'REVISAO')
        self.assertEqual(result['alertas'],[])
        self.assertFalse(result['cobertura_completa'])

    def test_buffer_proximidade_nao_vira_intersecao(self):
        result=evaluate(polygon(),{'AMAZONIA':dataset(polygon(x=-54.9985))})
        self.assertEqual(result['status'],'REVISAO')
        self.assertGreater(result['alertas'][0]['distancia_m'],40)
        self.assertLess(result['alertas'][0]['distancia_m'],100)
        self.assertEqual(result['alertas'][0]['area_intersecao_m2'],0)

    def test_degradacao_nao_e_rotulada_desmatamento(self):
        result=evaluate(polygon(),{'AMAZONIA':dataset(category='DEGRADACAO')})
        self.assertEqual(result['status'],'REVISAO')
        self.assertFalse(result['alertas'][0]['bloqueante'])

    def test_poligono_auto_intersectante_rejeitado(self):
        with self.assertRaises(ValueError):geometry({})
        with self.assertRaises(ValueError):
            geometry({'type':'Polygon','coordinates':[[[-55,-10],[-54,-9],[-55,-9],[-54,-10],[-55,-10]]]})

    @patch('lavouraInteligente.ambiental.urlopen')
    def test_resposta_truncada_nao_vira_ausencia_de_risco(self,open_url):
        data={'type':'FeatureCollection','features':[],'totalFeatures':1}
        open_url.return_value.__enter__.return_value.read.return_value=json.dumps(data).encode()
        with self.assertRaises(ValueError):fetch_layer('deter-amz:deter_amz',[-55,-10,-54,-9])


class IntegrationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed',verbosity=0)

    def setUp(self):
        self.plot=Talhao.objects.first()
        self.plot.poligono=polygon();self.plot.status='APROVADO';self.plot.save()
        EntregaCloud.objects.all().delete()

    @patch('lavouraInteligente.ambiental.fetch_layer')
    def test_snapshot_persistido_outbox_atomicamente_e_bloqueio_preservado(self,fetch):
        fetch.return_value=(dataset(),'abc','https://example.invalid/query')
        row=analyze(self.plot.pk)
        self.assertEqual(row.status,'BLOQUEADO')
        self.assertEqual(row.poligono_sha256,hashlib.sha256(canonical(polygon())).hexdigest())
        self.assertEqual(EntregaCloud.objects.filter(tipo='EVIDENCIA').count(),2)
        fetch.side_effect=TimeoutError()
        later=analyze(self.plot.pk)
        self.assertEqual(later.status,'BLOQUEADO')
        self.assertIn('falhas_fontes',later.resultado)
        self.assertEqual(AnaliseAmbiental.objects.count(),2)

    @patch('lavouraInteligente.ambiental.fetch_layer')
    def test_sem_fontes_fica_em_revisao_com_falhas_visiveis(self,fetch):
        fetch.side_effect=TimeoutError()
        row=analyze(self.plot.pk)
        self.assertEqual(row.status,'REVISAO')
        self.assertEqual(len(row.resultado['falhas_fontes']),2)

    @patch('lavouraInteligente.ambiental.fetch_layer')
    def test_edicao_concorrente_do_poligono_nao_aplica_resultado_antigo(self,fetch):
        def change(*args):
            Talhao.objects.filter(pk=self.plot.pk).update(poligono=polygon(x=-56))
            return dataset(),'abc','https://example.invalid/query'
        fetch.side_effect=change
        with self.assertRaises(ValueError):analyze(self.plot.pk)
        self.assertFalse(AnaliseAmbiental.objects.exists())

    @patch.dict(os.environ,{'RAIZES_S3_BUCKET':'test-bucket','RAIZES_DYNAMODB_TABLE':'test-table','RAIZES_SNS_TOPIC_ARN':'test-topic'})
    @patch('lavouraInteligente.cloud.deliver')
    def test_falha_cloud_permanece_para_retry_sem_segredos(self,send):
        row=EntregaCloud.objects.create(tipo='EVIDENCIA',chave='a.json',conteudo={'a':1})
        send.side_effect=TimeoutError('sensitive detail not to log')
        self.assertEqual(flush()['falhas'],1)
        row.refresh_from_db();self.assertEqual(row.erro,'TimeoutError');self.assertIsNone(row.enviado_em)
        send.side_effect=None
        self.assertEqual(flush()['enviados'],1)
        row.refresh_from_db();self.assertEqual(row.tentativas,2);self.assertIsNotNone(row.enviado_em)

    @patch.dict(os.environ,{'RAIZES_DYNAMODB_TABLE':'test-table'})
    def test_dynamodb_nao_sobrescreve_versao_mais_recente(self):
        client=boto3.client('dynamodb',region_name='us-east-2',aws_access_key_id='test',aws_secret_access_key='test')
        row=EntregaCloud.objects.create(tipo='STATUS',chave='TALHAO#1',conteudo={'status':'BLOQUEADO'})
        with Stubber(client) as stub:
            stub.add_client_error('put_item',service_error_code='ConditionalCheckFailedException',
                expected_params={'TableName':'test-table','Item':ANY,
                    'ConditionExpression':'attribute_not_exists(versao) OR versao <= :v',
                    'ExpressionAttributeValues':{':v':{'N':str(row.id)}}})
            with patch('lavouraInteligente.cloud.client',return_value=client):deliver(row)
            stub.assert_no_pending_responses()

    def test_api_mutacoes_exigem_equipe(self):
        response=self.client.post('/api/produtores/',{'nome':'sem autorização'})
        self.assertEqual(response.status_code,403)
        self.assertEqual(self.client.get('/api/').status_code,200)

    def test_status_efetivo_recusa_analise_vencida_e_geometria_alterada(self):
        from .risco import status_efetivo
        from django.utils import timezone
        from datetime import timedelta
        self.plot.atributos['analise_ambiental']={'valido_ate':(timezone.now()-timedelta(seconds=1)).isoformat(),
            'poligono_sha256':hashlib.sha256(canonical(self.plot.poligono)).hexdigest()}
        self.assertEqual(status_efetivo(self.plot),'REVISAO')
        self.plot.atributos['analise_ambiental']['valido_ate']=(timezone.now()+timedelta(hours=1)).isoformat()
        self.assertEqual(status_efetivo(self.plot),'APROVADO')
        self.plot.poligono=polygon(x=-56)
        self.assertEqual(status_efetivo(self.plot),'REVISAO')

    def test_novo_talhao_nao_pode_forjar_aprovacao_pela_api(self):
        from django.contrib.auth import get_user_model
        self.client.force_login(get_user_model().objects.create_user('operador',is_staff=True))
        response=self.client.post('/api/talhoes/',{'fazenda':self.plot.fazenda_id,'codigo':'SEM-APROVACAO',
            'cultura':'soja','area_ha':'1.00','status':'APROVADO'})
        self.assertEqual(response.status_code,201)
        self.assertEqual(response.json()['status'],'REVISAO')

    def test_validade_da_analise_nao_pode_ser_forjada_pela_api(self):
        from django.contrib.auth import get_user_model
        self.client.force_login(get_user_model().objects.create_user('operador',is_staff=True))
        response=self.client.patch(f'/api/talhoes/{self.plot.pk}/',json.dumps({'atributos':{
            'analise_ambiental':{'valido_ate':'2099-01-01T00:00:00Z'}}}),content_type='application/json')
        self.assertEqual(response.status_code,400)

    def test_decisao_reconsulta_origem_apos_alerta_novo(self):
        from django.contrib.auth import get_user_model
        from .models import Lote,LoteTalhao
        self.client.force_login(get_user_model().objects.create_user('operador',is_staff=True))
        lot=Lote.objects.create(codigo='ANTES-DO-ALERTA',peso_total_kg=1,status='APROVADO')
        LoteTalhao.objects.create(lote=lot,talhao=self.plot,peso_kg=1)
        self.plot.status='BLOQUEADO';self.plot.save()
        response=self.client.post(f'/app/lotes/{lot.pk}/decisao/',json.dumps({'acao':'ACEITAR',
            'justificativa':'Tentativa posterior a alerta novo.'}),content_type='application/json')
        self.assertEqual(response.status_code,409)
        self.assertFalse(hasattr(lot,'decisao'))
