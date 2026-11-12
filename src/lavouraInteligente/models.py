from django.contrib.postgres.indexes import GinIndex
from django.db import models
from django.conf import settings
import uuid


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


class RevisaoStatus(models.Model):
    talhao = models.ForeignKey(Talhao, on_delete=models.PROTECT, related_name='revisoes')
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    status_anterior = models.CharField(max_length=10, choices=StatusRisco.choices)
    status_novo = models.CharField(max_length=10, choices=StatusRisco.choices)
    justificativa = models.TextField()
    evidencia_original = models.JSONField(default=dict)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-criado_em']


class DecisaoRecebimento(models.Model):
    lote = models.OneToOneField(Lote, on_delete=models.PROTECT, related_name='decisao')
    operador = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    acao = models.CharField(max_length=10, choices=[('ACEITAR','Aceitar'),('RECUSAR','Recusar')])
    status_consultado = models.CharField(max_length=10, choices=StatusRisco.choices)
    justificativa = models.TextField()
    criado_em = models.DateTimeField(auto_now_add=True)


class Vistoria(models.Model):
    ESTADOS = [('SOLICITADA','Solicitada'),('AGENDADA','Agendada'),('RECEBIDA','Recebida')]
    talhao = models.ForeignKey(Talhao, on_delete=models.PROTECT, related_name='vistorias')
    solicitante = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    motivo = models.TextField()
    prazo = models.DateField()
    status = models.CharField(max_length=12, choices=ESTADOS, default='SOLICITADA')
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-criado_em']
        constraints = [models.UniqueConstraint(fields=['talhao'],
            condition=models.Q(status__in=['SOLICITADA','AGENDADA']),name='vistoria_aberta_por_talhao')]


class ArquivoVistoria(models.Model):
    vistoria = models.ForeignKey(Vistoria, on_delete=models.PROTECT, related_name='arquivos')
    arquivo = models.FileField(upload_to='vistorias/%Y/%m/')
    nome_original = models.CharField(max_length=255)
    sha256 = models.CharField(max_length=64)
    tamanho = models.PositiveBigIntegerField()
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    criado_em = models.DateTimeField(auto_now_add=True)


class EventoAuditoria(models.Model):
    ator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    acao = models.CharField(max_length=80)
    recurso = models.CharField(max_length=80)
    recurso_id = models.PositiveBigIntegerField(null=True)
    descricao = models.CharField(max_length=255)
    dados = models.JSONField(default=dict)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-criado_em']


class AnaliseAmbiental(models.Model):
    talhao = models.ForeignKey(Talhao, on_delete=models.PROTECT, related_name='analises')
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    poligono_sha256 = models.CharField(max_length=64)
    poligono = models.JSONField()
    status = models.CharField(max_length=10, choices=StatusRisco.choices)
    resultado = models.JSONField()
    datasets = models.JSONField(default=dict)
    criado_em = models.DateTimeField(auto_now_add=True)
    valido_ate = models.DateTimeField()

    class Meta:
        ordering = ['-criado_em']


class EntregaCloud(models.Model):
    tipo = models.CharField(max_length=20)
    chave = models.CharField(max_length=255)
    conteudo = models.JSONField()
    tentativas = models.PositiveIntegerField(default=0)
    erro = models.CharField(max_length=100, blank=True)
    enviado_em = models.DateTimeField(null=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['id']


class CenarioSimulado(models.Model):
    id = models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    idempotencia = models.UUIDField(unique=True,default=uuid.uuid4)
    talhao = models.OneToOneField(Talhao,on_delete=models.PROTECT,related_name='cenario_simulado')
    cenario = models.CharField(max_length=30)
    autor = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True)
    dados = models.JSONField(default=dict)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-criado_em']


class UploadSimulado(models.Model):
    id = models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    cenario = models.ForeignKey(CenarioSimulado,on_delete=models.PROTECT,related_name='uploads')
    vistoria = models.ForeignKey(Vistoria,on_delete=models.PROTECT,related_name='voos_simulados')
    autor = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True)
    perfil_voo = models.CharField(max_length=30)
    poligono_sha256 = models.CharField(max_length=64)
    cobertura = models.JSONField(null=True)
    data_voo = models.DateField()
    tamanho_declarado = models.PositiveBigIntegerField(default=5*1024**3)
    total_partes = models.PositiveIntegerField(default=10)
    partes = models.JSONField(default=dict)
    status = models.CharField(max_length=30,default='EM_ENVIO')
    validacao = models.JSONField(default=dict)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-criado_em']
