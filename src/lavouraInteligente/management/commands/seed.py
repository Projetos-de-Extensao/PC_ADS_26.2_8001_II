from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from lavouraInteligente.models import Fazenda, Lote, LoteTalhao, Produtor, StatusRisco, Talhao


def quadrado(lon, lat, d=0.01):
    return {
        "type": "Polygon",
        "coordinates": [[[lon, lat], [lon + d, lat], [lon + d, lat + d], [lon, lat + d], [lon, lat]]],
    }


TALHOES = [
    # codigo, fazenda, cultura, area, status, atributos, (lon, lat)
    ("TALHAO_8F23", "Fazenda Santa Rita", "soja", "120.50", StatusRisco.APROVADO,
     {"bioma": "cerrado", "ndvi": 0.78, "fonte": "MapBiomas", "alertas": []}, (-47.90, -15.80)),
    ("TALHAO_10023", "Fazenda Santa Rita", "soja", "98.00", StatusRisco.REVISAO,
     {"bioma": "cerrado", "ndvi": 0.41, "fonte": "DETER", "alertas": ["DETER-2026-09-21"]}, (-47.88, -15.80)),
    ("TALHAO_C401", "Sitio Boa Vista", "cafe", "35.20", StatusRisco.APROVADO,
     {"bioma": "mata_atlantica", "ndvi": 0.82, "fonte": "Sentinel", "certificacao": "Rainforest"}, (-45.40, -21.50)),
    ("TALHAO_A777", "Fazenda Rio Verde", "cacau", "60.00", StatusRisco.BLOQUEADO,
     {"bioma": "amazonia", "ndvi": 0.22, "fonte": "DETER", "alertas": ["DETER-2026-08-02", "DETER-2026-09-10"]},
     (-52.30, -3.20)),
]


class Command(BaseCommand):
    help = "Cria dados de exemplo do tema (idempotente)."

    @transaction.atomic
    def handle(self, *args, **options):
        joao, _ = Produtor.objects.get_or_create(
            documento="123.456.789-00", defaults={"nome": "João Pereira", "municipio": "Cristalina", "uf": "GO"})
        maria, _ = Produtor.objects.get_or_create(
            documento="12.345.678/0001-90", defaults={"nome": "Maria Souza", "municipio": "Altamira", "uf": "PA"})
        fazendas = {
            "Fazenda Santa Rita": (joao, "GO-5205-ABCD", "Cristalina", "GO", "500.00"),
            "Sitio Boa Vista": (joao, "MG-3106-EFGH", "Varginha", "MG", "80.00"),
            "Fazenda Rio Verde": (maria, "PA-1500-IJKL", "Altamira", "PA", "900.00"),
        }
        objs = {}
        for nome, (prod, car, mun, uf, area) in fazendas.items():
            objs[nome], _ = Fazenda.objects.get_or_create(
                nome=nome, produtor=prod,
                defaults={"car_codigo": car, "municipio": mun, "uf": uf, "area_ha": Decimal(area)})
        for codigo, faz, cultura, area, st, atributos, (lon, lat) in TALHOES:
            Talhao.objects.get_or_create(
                codigo=codigo,
                defaults={"fazenda": objs[faz], "cultura": cultura, "area_ha": Decimal(area), "status": st,
                          "atributos": atributos, "poligono": quadrado(lon, lat)})
        lote, criado = Lote.objects.get_or_create(
            codigo="2026-09-00128",
            defaults={"peso_total_kg": Decimal("32000.00"), "status": StatusRisco.APROVADO,
                      "motivo": "Polígono válido, origem rastreável e nenhuma ocorrência crítica ativa."})
        if criado:
            LoteTalhao.objects.create(lote=lote, talhao=Talhao.objects.get(codigo="TALHAO_8F23"),
                                      peso_kg=Decimal("32000.00"))
        self.stdout.write(self.style.SUCCESS(
            f"Seed ok: {Produtor.objects.count()} produtores, {Fazenda.objects.count()} fazendas, "
            f"{Talhao.objects.count()} talhões, {Lote.objects.count()} lotes."))
