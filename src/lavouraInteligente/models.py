from django.contrib.postgres.indexes import GinIndex
from django.db import models


class StatusRisco(models.TextChoices):
    """Status de risco operacional (RN-01: não é certificação jurídica)."""

    APROVADO = "APROVADO", "Aprovado"
    REVISAO = "REVISAO", "Revisão"
    BLOQUEADO = "BLOQUEADO", "Bloqueado"


class Produtor(models.Model):
    nome = models.CharField(max_length=200)
    documento = models.CharField("CPF/CNPJ", max_length=20, unique=True)
    municipio = models.CharField(max_length=120)
    uf = models.CharField(max_length=2)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["nome"]
        verbose_name_plural = "produtores"

    def __str__(self):
        return self.nome


class Fazenda(models.Model):
    produtor = models.ForeignKey(Produtor, on_delete=models.CASCADE, related_name="fazendas")
    nome = models.CharField(max_length=200)
    car_codigo = models.CharField("código CAR", max_length=60, blank=True)
    municipio = models.CharField(max_length=120)
    uf = models.CharField(max_length=2)
    area_ha = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class Talhao(models.Model):
    fazenda = models.ForeignKey(Fazenda, on_delete=models.CASCADE, related_name="talhoes")
    codigo = models.CharField(max_length=40, unique=True)
    cultura = models.CharField(max_length=60)
    area_ha = models.DecimalField(max_digits=10, decimal_places=2)
    # Documento: polígono GeoJSON do talhão.
    poligono = models.JSONField(default=dict, blank=True)
    # Documento: atributos flexíveis (bioma, NDVI, alertas, fonte...). Indexado com GIN.
    atributos = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=10, choices=StatusRisco.choices, default=StatusRisco.APROVADO)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["codigo"]
        verbose_name = "talhão"
        verbose_name_plural = "talhões"
        indexes = [GinIndex(fields=["atributos"], name="talhao_atributos_gin")]

    def __str__(self):
        return self.codigo


class Lote(models.Model):
    codigo = models.CharField(max_length=40, unique=True)
    recebido_em = models.DateTimeField(auto_now_add=True)
    peso_total_kg = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=10, choices=StatusRisco.choices, default=StatusRisco.APROVADO)
    motivo = models.TextField(blank=True)
    talhoes = models.ManyToManyField(Talhao, through="LoteTalhao", related_name="lotes")

    class Meta:
        ordering = ["-recebido_em"]

    def __str__(self):
        return self.codigo


class LoteTalhao(models.Model):
    """Tabela associativa Lote x Talhão com o peso de origem de cada talhão."""

    lote = models.ForeignKey(Lote, on_delete=models.CASCADE, related_name="itens")
    talhao = models.ForeignKey(Talhao, on_delete=models.PROTECT, related_name="entregas")
    peso_kg = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["lote", "talhao"], name="lote_talhao_unico")]
        verbose_name = "item do lote"
        verbose_name_plural = "itens do lote"

    def __str__(self):
        return f"{self.lote} <- {self.talhao}"
