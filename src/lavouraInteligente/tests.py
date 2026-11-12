from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import connection
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Fazenda, Lote, LoteTalhao, Produtor, StatusRisco, Talhao


class BaseDados(APITestCase):
    def setUp(self):
        self.client.force_authenticate(get_user_model().objects.create_user('teste-api',is_staff=True))
        self.produtor = Produtor.objects.create(nome="João", documento="111", municipio="Cristalina", uf="GO")
        self.fazenda = Fazenda.objects.create(
            produtor=self.produtor, nome="Santa Rita", municipio="Cristalina", uf="GO", area_ha=Decimal("500"))
        self.ok = Talhao.objects.create(
            fazenda=self.fazenda, codigo="T_OK", cultura="soja", area_ha=Decimal("10"),
            poligono={"type":"Polygon","coordinates":[[[-55,-10],[-54.99,-10],[-54.99,-9.99],[-55,-9.99],[-55,-10]]]},
            atributos={"bioma": "cerrado", "ndvi": 0.8, "fonte": "MapBiomas"})
        self.suspeito = Talhao.objects.create(
            fazenda=self.fazenda, codigo="T_SUSP", cultura="soja", area_ha=Decimal("10"),
            status=StatusRisco.REVISAO, atributos={"bioma": "cerrado", "ndvi": 0.4, "fonte": "DETER"})
        self.bloqueado = Talhao.objects.create(
            fazenda=self.fazenda, codigo="T_BLOQ", cultura="cacau", area_ha=Decimal("10"),
            status=StatusRisco.BLOQUEADO, atributos={"bioma": "amazonia", "ndvi": 0.2, "fonte": "DETER"})


class RelacionalTests(BaseDados):
    def test_crud_e_serializer_aninhado(self):
        resp = self.client.post("/api/produtores/", {"nome": "Maria", "documento": "222",
                                                      "municipio": "Altamira", "uf": "PA"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        resp = self.client.get(f"/api/produtores/{self.produtor.id}/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        talhoes = resp.data["fazendas"][0]["talhoes"]
        self.assertEqual({t["codigo"] for t in talhoes}, {"T_OK", "T_SUSP", "T_BLOQ"})

    def test_relacionamentos(self):
        lote = Lote.objects.create(codigo="L1", peso_total_kg=Decimal("5"))
        LoteTalhao.objects.create(lote=lote, talhao=self.ok, peso_kg=Decimal("5"))
        self.assertEqual(list(lote.talhoes.all()), [self.ok])
        self.assertEqual(self.ok.fazenda.produtor, self.produtor)


class DocumentoJsonbTests(BaseDados):
    def test_filtro_por_chave_json(self):
        resp = self.client.get("/api/talhoes/?atributos__bioma=cerrado")
        self.assertEqual({t["codigo"] for t in resp.data}, {"T_OK", "T_SUSP"})
        resp = self.client.get("/api/talhoes/?atributos__ndvi__gte=0.5")
        self.assertEqual([t["codigo"] for t in resp.data], ["T_OK"])
        resp = self.client.get('/api/talhoes/?atributos__contains={"fonte": "DETER"}')
        self.assertEqual({t["codigo"] for t in resp.data}, {"T_SUSP", "T_BLOQ"})

    def test_chave_json_inexistente_retorna_lista_vazia(self):
        resp = self.client.get("/api/talhoes/?atributos__certificacao=Rainforest")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data, [])

    def test_indice_gin_criado_pela_migration(self):
        with connection.cursor() as cur:
            cur.execute("SELECT indexdef FROM pg_indexes WHERE indexname = 'talhao_atributos_gin'")
            linha = cur.fetchone()
        self.assertIsNotNone(linha)
        self.assertIn("USING gin", linha[0])


class TransacaoTests(BaseDados):
    url = "/api/lotes/receber/"

    def test_recebimento_grava_lote_e_itens(self):
        resp = self.client.post(self.url, {"codigo": "L-OK", "peso_total_kg": "300.00", "itens": [
            {"talhao": self.ok.id, "peso_kg": "200.00"},
            {"talhao": self.suspeito.id, "peso_kg": "100.00"}]}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        self.assertEqual(resp.data["status"], StatusRisco.REVISAO)
        self.assertEqual(LoteTalhao.objects.filter(lote__codigo="L-OK").count(), 2)

    def test_lote_assume_pior_status_bloqueado(self):
        resp = self.client.post(self.url, {"codigo": "L-BLOQ", "peso_total_kg": "300.00", "itens": [
            {"talhao": self.ok.id, "peso_kg": "200.00"},
            {"talhao": self.bloqueado.id, "peso_kg": "100.00"}]}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        self.assertEqual(resp.data["status"], StatusRisco.BLOQUEADO)
        self.assertIn("T_BLOQ", resp.data["motivo"])

    def test_soma_de_pesos_divergente_faz_rollback(self):
        resp = self.client.post(self.url, {"codigo": "L-PESO", "peso_total_kg": "999.00", "itens": [
            {"talhao": self.ok.id, "peso_kg": "200.00"}]}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_409_CONFLICT)
        self.assertFalse(Lote.objects.filter(codigo="L-PESO").exists())
        self.assertEqual(LoteTalhao.objects.count(), 0)

    def test_talhao_repetido_faz_rollback(self):
        resp = self.client.post(self.url, {"codigo": "L-REP", "peso_total_kg": "200.00", "itens": [
            {"talhao": self.ok.id, "peso_kg": "100.00"},
            {"talhao": self.ok.id, "peso_kg": "100.00"}]}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(Lote.objects.count(), 0)
        self.assertEqual(LoteTalhao.objects.count(), 0)


class AdminSeedTests(APITestCase):
    def test_seed_idempotente_e_admin(self):
        call_command("seed", verbosity=0)
        call_command("seed", verbosity=0)
        self.assertEqual(Talhao.objects.count(), 4)
        self.assertEqual(Lote.objects.count(), 1)
        get_user_model().objects.create_superuser("admin", "a@a.com", "senha-teste-123")
        self.client.login(username="admin", password="senha-teste-123")
        for url in ["/admin/", "/admin/lavouraInteligente/talhao/", "/admin/lavouraInteligente/lote/"]:
            self.assertEqual(self.client.get(url).status_code, 200, url)


class CrudCompletoTests(BaseDados):
    def test_crud_dos_cinco_recursos(self):
        recursos = []

        def criar(nome, dados, alteracao):
            resposta = self.client.post(f'/api/{nome}/', dados, format='json')
            self.assertEqual(resposta.status_code, 201, resposta.data)
            url = f'/api/{nome}/{resposta.data["id"]}/'
            atual = self.client.get(url)
            self.assertEqual(atual.status_code, 200)
            self.assertEqual(self.client.get(f'/api/{nome}/').status_code, 200)
            completa = self.client.put(url, atual.data, format='json')
            self.assertEqual(completa.status_code, 200, completa.data)
            parcial = self.client.patch(url, alteracao, format='json')
            self.assertEqual(parcial.status_code, 200, parcial.data)
            for chave, valor in alteracao.items():
                self.assertEqual(parcial.data[chave], valor)
            recursos.append(url)
            return resposta.data['id']

        produtor = criar('produtores', {'nome':'CRUD','documento':'crud-1',
                         'municipio':'Cristalina','uf':'GO'}, {'nome':'Atualizado'})
        fazenda = criar('fazendas', {'produtor':produtor,'nome':'CRUD','municipio':'Cristalina',
                        'uf':'GO','area_ha':'10.00'}, {'nome':'Atualizada'})
        talhao = criar('talhoes', {'fazenda':fazenda,'codigo':'CRUD-T','cultura':'soja',
                       'area_ha':'2.00'}, {'cultura':'milho'})
        lote = criar('lotes', {'codigo':'CRUD-L','peso_total_kg':'100.00'}, {'motivo':'CRUD'})
        criar('lote-itens', {'lote':lote,'talhao':talhao,'peso_kg':'100.00'}, {'peso_kg':'99.00'})
        for url in reversed(recursos):
            self.assertEqual(self.client.delete(url).status_code, 204, url)
            self.assertEqual(self.client.get(url).status_code, 404, url)

    def test_talhao_sem_poligono_exige_revisao_no_recebimento(self):
        self.ok.poligono = {}
        self.ok.save(update_fields=['poligono'])
        resposta = self.client.post('/api/lotes/receber/', {
            'codigo':'L-SEM-POLIGONO','peso_total_kg':'10.00',
            'itens':[{'talhao':self.ok.id,'peso_kg':'10.00'}]}, format='json')
        self.assertEqual(resposta.status_code, 201, resposta.data)
        self.assertEqual(resposta.data['status'], StatusRisco.REVISAO)
