import hashlib
import io
import json
import uuid
import zipfile
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import Client,TestCase

from .acesso import capacidades
from .ambiental import analyze,canonical
from .models import (AnaliseAmbiental,CenarioSimulado,DecisaoRecebimento,EntregaCloud,
                     Lote,LoteTalhao,Talhao,UploadSimulado,Vistoria)
from .simulacao import criar,iniciar_voo,enviar_parte,concluir_voo


class LaboratorioTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed',verbosity=0)
        call_command('configurar_perfis',verbosity=0)
        cls.user=get_user_model().objects.create_user('gestor-test',is_staff=True)

    def setUp(self):self.client.force_login(self.user)

    def post(self,url,data):return self.client.post(url,json.dumps(data),content_type='application/json')

    def upload_completo(self,run,profile='valido'):
        row=iniciar_voo(run,profile,self.user)
        for n in range(1,row.total_partes+1):enviar_parte(row.pk,n)
        return concluir_voo(row.pk,self.user)

    @patch('lavouraInteligente.ambiental.fetch_layer')
    def test_seis_cenarios_sem_consultar_provedores_reais(self,fetch):
        expected={'livre':'APROVADO','proximidade':'REVISAO','desmatamento':'BLOQUEADO',
            'nuvens':'REVISAO','fonte_indisponivel':'REVISAO','vencido':'REVISAO'}
        for scenario,status in expected.items():
            run=criar(scenario,self.user)
            self.assertEqual(run.talhao.status,status)
            self.assertTrue(run.dados['resultado']['simulado'])
            self.assertTrue(all(f['simulado'] for f in run.dados['resultado']['fontes']))
            self.assertEqual(run.talhao.atributos['ambiente'],'SIMULACAO')
        fetch.assert_not_called()
        self.assertEqual(CenarioSimulado.objects.count(),6)

    def test_chave_idempotente_nao_duplica_dados_ou_entregas(self):
        key=uuid.uuid4();first=criar('livre',self.user,key);count=EntregaCloud.objects.count()
        second=criar('livre',self.user,key)
        self.assertEqual(first.pk,second.pk)
        self.assertEqual(CenarioSimulado.objects.count(),1)
        self.assertEqual(EntregaCloud.objects.count(),count)

    def test_fontes_reais_nao_sobrescrevem_o_laboratorio(self):
        run=criar('livre',self.user)
        with self.assertRaises(ValueError):analyze(run.talhao_id)
        self.assertEqual(self.post(f'/app/talhoes/{run.talhao_id}/analisar/',{}).status_code,409)

    def test_projecaodynamo_separa_chaves_simuladas(self):
        run=criar('livre',self.user)
        rows=EntregaCloud.objects.filter(tipo='STATUS',chave=f'DEMO#TALHAO#{run.talhao_id}')
        self.assertTrue(rows.exists())
        self.assertTrue(all(r.conteudo['simulado'] for r in rows))
        self.assertFalse(EntregaCloud.objects.filter(tipo='STATUS',chave=f'TALHAO#{run.talhao_id}').exists())

    def test_partes_repetidas_sao_idempotentes_e_persistem(self):
        run=criar('proximidade',self.user);upload=iniciar_voo(run,'valido',self.user)
        enviar_parte(upload.pk,1);enviar_parte(upload.pk,1);enviar_parte(upload.pk,2)
        upload.refresh_from_db();self.assertEqual(set(upload.partes),{'1','2'})
        data=Client();data.force_login(self.user)
        saved=data.get('/app/laboratorio/').json()['execucoes'][0]['uploads'][0]
        self.assertEqual(saved['partes'],[1,2]);self.assertEqual(saved['bytes_reais_transferidos'],0)

    def test_nao_finaliza_upload_incompleto(self):
        row=iniciar_voo(criar('proximidade',self.user),'valido',self.user)
        enviar_parte(row.pk,1)
        self.assertEqual(self.post(f'/app/laboratorio/voos/{row.pk}/finalizar/',{}).status_code,400)
        row.refresh_from_db();self.assertEqual(row.status,'EM_ENVIO')

    def test_voo_valido_calcula_cobertura_sem_aprovar_automaticamente(self):
        run=criar('nuvens',self.user);row=self.upload_completo(run)
        self.assertEqual(row.status,'VALIDADO')
        self.assertGreaterEqual(row.validacao['cobertura_percentual'],95)
        self.assertEqual(row.validacao['manifesto']['bytes_reais_transferidos'],0)
        row.vistoria.refresh_from_db();self.assertEqual(row.vistoria.status,'RECEBIDA')
        run.talhao.refresh_from_db();self.assertEqual(run.talhao.status,'REVISAO')
        original=canonical(row.validacao['manifesto'])
        self.assertEqual(row.validacao['sha256'],hashlib.sha256(original).hexdigest())

    def test_cobertura_insuficiente_nao_e_recebida_como_evidencia_valida(self):
        run=criar('proximidade',self.user);row=self.upload_completo(run,'cobertura_insuficiente')
        self.assertEqual(row.status,'REJEITADO');self.assertFalse(row.validacao['apto_para_revisao'])
        self.assertLess(row.validacao['cobertura_percentual'],95)
        row.vistoria.refresh_from_db();self.assertEqual(row.vistoria.status,'AGENDADA')

    def test_data_antiga_e_ausencia_de_georreferencia_recusadas(self):
        for profile in ['antigo','sem_georreferencia']:
            run=criar('proximidade',self.user);row=self.upload_completo(run,profile)
            self.assertEqual(row.status,'REJEITADO');self.assertTrue(row.validacao['erros'])

    def test_poligono_alterado_durante_upload_exige_novo_voo(self):
        run=criar('proximidade',self.user);row=iniciar_voo(run,'valido',self.user)
        for n in range(1,11):enviar_parte(row.pk,n)
        Talhao.objects.filter(pk=run.talhao_id).update(poligono={})
        with self.assertRaises(ValueError):concluir_voo(row.pk,self.user)
        row.refresh_from_db();self.assertEqual(row.status,'EM_ENVIO')

    def test_revisao_so_aprova_cenario_com_voo_valido(self):
        run=criar('proximidade',self.user)
        url=f'/app/talhoes/{run.talhao_id}/revisar/'
        data={'status':'APROVADO','justificativa':'Vistoria virtual conferida para a apresentação.'}
        self.assertEqual(self.post(url,data).status_code,409)
        self.upload_completo(run)
        self.assertEqual(self.post(url,data).status_code,201)

    def test_lote_misto_faz_rollback_completo(self):
        run=criar('livre',self.user);operational=Talhao.objects.get(codigo='TALHAO_8F23')
        before=Lote.objects.count()
        response=self.post('/api/lotes/receber/',{'codigo':'MISTURA-INVALIDA','peso_total_kg':'2.00',
            'itens':[{'talhao':run.talhao_id,'peso_kg':'1.00'},{'talhao':operational.pk,'peso_kg':'1.00'}]})
        self.assertEqual(response.status_code,409)
        self.assertEqual(Lote.objects.count(),before)
        self.assertFalse(LoteTalhao.objects.filter(lote__codigo='MISTURA-INVALIDA').exists())

    def test_dossie_com_analise_voo_geometria_auditoria_e_hashes(self):
        run=criar('nuvens',self.user);row=self.upload_completo(run)
        response=self.client.get(f'/app/exportar/talhao/{run.talhao_id}/')
        raw=b''.join(response.streaming_content)
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            manifest=json.loads(archive.read('manifesto.json'))
            self.assertTrue(manifest['simulado'])
            self.assertIn(f'vistorias-simuladas/{row.pk}.json',archive.namelist())
            self.assertTrue(any(name.startswith('analises/') for name in archive.namelist()))
            self.assertTrue(any(name.startswith('geometrias/') for name in archive.namelist()))
            for name,digest in manifest['arquivos'].items():self.assertEqual(hashlib.sha256(archive.read(name)).hexdigest(),digest)

    def test_relatorio_separa_demonstracao_e_registros_operacionais(self):
        criar('livre',self.user)
        result=self.client.get('/app/relatorios/').json()
        self.assertEqual({r['ambiente'] for r in result['linhas']},{'SIMULACAO','OPERACIONAL'})
        response=self.client.get('/app/relatorios/exportar/')
        self.assertEqual(response.status_code,200);self.assertIn('SIMULACAO',response.content.decode('utf-8'))

    def test_auditor_nao_executa_nem_altera_cadastros(self):
        self.user.groups.add(Group.objects.get(name='Auditor'))
        self.assertEqual(self.post('/app/laboratorio/executar/',{'cenario':'livre'}).status_code,403)
        self.assertEqual(self.post('/api/produtores/',{'nome':'bloqueado'}).status_code,403)
        self.assertEqual(self.client.get('/app/relatorios/exportar/').status_code,200)

    def test_piloto_envia_voo_mas_nao_decide_risco(self):
        run=criar('proximidade',self.user)
        self.user.groups.add(Group.objects.get(name='Piloto'))
        self.assertEqual(self.post(f'/app/laboratorio/{run.pk}/voos/',{'perfil':'valido'}).status_code,201)
        self.assertEqual(self.post(f'/app/talhoes/{run.talhao_id}/revisar/',{
            'status':'APROVADO','justificativa':'Tentativa fora do papel de piloto.'}).status_code,403)

    def test_analista_nao_registra_decisao_de_balanca(self):
        self.user.groups.add(Group.objects.get(name='Analista'))
        self.assertEqual(self.post('/api/lotes/receber/',{'codigo':'nao-criar'}).status_code,403)
        self.assertEqual(self.post('/app/laboratorio/executar/',{'cenario':'livre'}).status_code,201)

    def test_operador_recebe_e_decide_sem_alterar_cadastros(self):
        self.user.groups.add(Group.objects.get(name='Operador da balança'))
        self.assertEqual(self.post('/api/produtores/',{'nome':'fora-do-perfil'}).status_code,403)
        plot=Talhao.objects.get(codigo='TALHAO_8F23')
        response=self.post('/api/lotes/receber/',{'codigo':'PERFIL-OPERADOR','peso_total_kg':'1.00',
            'itens':[{'talhao':plot.pk,'peso_kg':'1.00'}]})
        self.assertEqual(response.status_code,201)
        self.assertEqual(self.post(f'/app/lotes/{response.json()["id"]}/decisao/',{
            'acao':'ACEITAR','justificativa':'Origens conferidas pelo operador autorizado.'}).status_code,201)

    def test_desenho_historico_usa_poligono_preservado(self):
        run=criar('nuvens',self.user);row=self.upload_completo(run)
        original=run.talhao.poligono
        Talhao.objects.filter(pk=run.talhao_id).update(poligono={})
        response=self.client.get(f'/app/laboratorio/voos/{row.pk}/desenho/')
        self.assertEqual(response.status_code,200)
        self.assertEqual(row.validacao['manifesto']['poligono'],original)
        self.assertIn('SIMULAÇÃO',response.content.decode('utf-8'))

    def test_sem_sessao_nao_acessa_laboratorio(self):
        self.client.logout();self.assertEqual(self.client.get('/app/laboratorio/').status_code,302)

    def test_partes_invalidas_e_envio_cancelado_recusados(self):
        row=iniciar_voo(criar('proximidade',self.user),'valido',self.user)
        for value in [0,11,True,'1']:
            self.assertEqual(self.post(f'/app/laboratorio/voos/{row.pk}/partes/',{'parte':value}).status_code,400)
        self.assertEqual(self.post(f'/app/laboratorio/voos/{row.pk}/cancelar/',{}).status_code,200)
        self.assertEqual(self.post(f'/app/laboratorio/voos/{row.pk}/partes/',{'parte':1}).status_code,400)

    def test_lote_decidido_nao_permite_alterar_itens(self):
        run=criar('livre',self.user);lot=Lote.objects.create(codigo='FINALIZADO',peso_total_kg=1)
        item=LoteTalhao.objects.create(lote=lot,talhao=run.talhao,peso_kg=1)
        self.assertTrue(self.client.get(f'/api/lotes/{lot.pk}/').json()['simulado'])
        DecisaoRecebimento.objects.create(lote=lot,operador=self.user,acao='ACEITAR',status_consultado='APROVADO',justificativa='Conferido para demonstração.')
        self.assertEqual(self.client.delete(f'/api/lote-itens/{item.pk}/').status_code,409)
        self.assertEqual(self.client.patch(f'/api/lote-itens/{item.pk}/',json.dumps({'peso_kg':'2.00'}),content_type='application/json').status_code,400)
