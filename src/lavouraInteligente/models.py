from django.contrib.postgres.indexes import GinIndex
from django.db import models
from django.conf import settings
import uuid
from decimal import Decimal
from django.core.validators import MinValueValidator
from .validacao import UF_CHOICES, normalizar_documento, DOCUMENTO_DEMO, validar_documento
from .restricoes import dominio, preenchido, positivo, sha256, objeto, uf


class StatusRisco(models.TextChoices):
    """Status de risco operacional (RN-01: não é certificação jurídica)."""

    APROVADO = "APROVADO", "Aprovado"
    REVISAO = "REVISAO", "Revisão"
    BLOQUEADO = "BLOQUEADO", "Bloqueado"


class Produtor(models.Model):
    nome = models.CharField(max_length=200)
    documento = models.CharField("CPF/CNPJ", max_length=14, unique=True)
    simulado = models.BooleanField(default=False, editable=False)
    municipio = models.CharField(max_length=120)
    uf = models.CharField(max_length=2, choices=UF_CHOICES)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["nome"]
        verbose_name_plural = "produtores"
        constraints = [preenchido('nome','produtor_nome_preenchido'),
            preenchido('municipio','produtor_municipio_preenchido'), uf('uf','produtor_uf_valida'),
            models.CheckConstraint(name='produtor_documento_valido', condition=(
                models.Q(simulado=True, documento=DOCUMENTO_DEMO) |
                (models.Q(simulado=False) & models.Q(models.Func(models.F('documento'),
                    function='raizes_documento_valido', output_field=models.BooleanField())))),
                violation_error_message='CPF/CNPJ inválido ou identificador de laboratório inconsistente.')]

    def clean(self):
        super().clean()
        self.documento = normalizar_documento(self.documento)
        if not (self.simulado and self.documento == DOCUMENTO_DEMO):
            validar_documento(self.documento)

    def save(self, *args, **kwargs):
        self.documento = normalizar_documento(self.documento)
        self.uf = self.uf.strip().upper()
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.nome


class Fazenda(models.Model):
    produtor = models.ForeignKey(Produtor, on_delete=models.PROTECT, related_name="fazendas")
    nome = models.CharField(max_length=200)
    car_codigo = models.CharField("código CAR", max_length=60, blank=True)
    municipio = models.CharField(max_length=120)
    uf = models.CharField(max_length=2, choices=UF_CHOICES)
    area_ha = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])

    class Meta:
        ordering = ["nome"]
        constraints = [preenchido('nome','fazenda_nome_preenchido'),
            preenchido('municipio','fazenda_municipio_preenchido'), uf('uf','fazenda_uf_valida'),
            positivo('area_ha',12,'fazenda_area_positiva')]

    def save(self, *args, **kwargs):
        self.uf = self.uf.strip().upper()
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.nome


class Talhao(models.Model):
    fazenda = models.ForeignKey(Fazenda, on_delete=models.PROTECT, related_name="talhoes")
    codigo = models.CharField(max_length=40, unique=True)
    cultura = models.CharField(max_length=60)
    area_ha = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
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
        constraints = [preenchido('codigo','talhao_codigo_preenchido'), preenchido('cultura','talhao_cultura_preenchida'),
            positivo('area_ha',10,'talhao_area_positiva'), dominio('status',StatusRisco.values,'talhao_status_valido'),
            objeto('poligono','talhao_poligono_objeto'), objeto('atributos','talhao_atributos_objeto')]

    def __str__(self):
        return self.codigo


class Lote(models.Model):
    codigo = models.CharField(max_length=40, unique=True)
    recebido_em = models.DateTimeField(auto_now_add=True)
    peso_total_kg = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    status = models.CharField(max_length=10, choices=StatusRisco.choices, default=StatusRisco.APROVADO)
    motivo = models.TextField(blank=True)
    talhoes = models.ManyToManyField(Talhao, through="LoteTalhao", related_name="lotes")

    class Meta:
        ordering = ["-recebido_em"]
        constraints = [preenchido('codigo','lote_codigo_preenchido'), positivo('peso_total_kg',12,'lote_peso_positivo'),
            dominio('status',StatusRisco.values,'lote_status_valido')]

    def __str__(self):
        return self.codigo


class LoteTalhao(models.Model):
    """Tabela associativa Lote x Talhão com o peso de origem de cada talhão."""

    lote = models.ForeignKey(Lote, on_delete=models.CASCADE, related_name="itens")
    talhao = models.ForeignKey(Talhao, on_delete=models.PROTECT, related_name="entregas")
    peso_kg = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])

    class Meta:
        constraints = [models.UniqueConstraint(fields=["lote", "talhao"], name="lote_talhao_unico"),
            positivo('peso_kg',12,'lote_item_peso_positivo')]
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
        constraints = [dominio('status_anterior',StatusRisco.values,'revisao_status_anterior_valido'),
            dominio('status_novo',StatusRisco.values,'revisao_status_novo_valido'),
            preenchido('justificativa','revisao_justificativa_preenchida'), objeto('evidencia_original','revisao_evidencia_objeto')]


class DecisaoRecebimento(models.Model):
    lote = models.OneToOneField(Lote, on_delete=models.PROTECT, related_name='decisao')
    operador = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    acao = models.CharField(max_length=10, choices=[('ACEITAR','Aceitar'),('RECUSAR','Recusar')])
    status_consultado = models.CharField(max_length=10, choices=StatusRisco.choices)
    justificativa = models.TextField()
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [dominio('acao',['ACEITAR','RECUSAR'],'decisao_acao_valida'),
            dominio('status_consultado',StatusRisco.values,'decisao_status_valido'),
            preenchido('justificativa','decisao_justificativa_preenchida'),
            models.CheckConstraint(condition=models.Q(acao='RECUSAR') | models.Q(status_consultado='APROVADO'),
                name='decisao_aceite_aprovado')]


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
            condition=models.Q(status__in=['SOLICITADA','AGENDADA']),name='vistoria_aberta_por_talhao'),
            dominio('status',['SOLICITADA','AGENDADA','RECEBIDA'],'vistoria_status_valido'),
            preenchido('motivo','vistoria_motivo_preenchido')]


class ArquivoVistoria(models.Model):
    vistoria = models.ForeignKey(Vistoria, on_delete=models.PROTECT, related_name='arquivos')
    arquivo = models.FileField(upload_to='vistorias/%Y/%m/')
    nome_original = models.CharField(max_length=255)
    sha256 = models.CharField(max_length=64)
    tamanho = models.PositiveBigIntegerField()
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [sha256('sha256','arquivo_sha256_valido'), preenchido('arquivo','arquivo_caminho_preenchido'),
            preenchido('nome_original','arquivo_nome_preenchido'),
            models.CheckConstraint(condition=models.Q(tamanho__gt=0), name='arquivo_tamanho_positivo')]


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
        constraints = [preenchido('acao','evento_acao_preenchida'), preenchido('recurso','evento_recurso_preenchido'),
            preenchido('descricao','evento_descricao_preenchida'), objeto('dados','evento_dados_objeto')]


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
        constraints = [sha256('poligono_sha256','analise_sha256_valido'), dominio('status',StatusRisco.values,'analise_status_valido'),
            objeto('poligono','analise_poligono_objeto'), objeto('resultado','analise_resultado_objeto'),
            objeto('datasets','analise_datasets_objeto')]


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
        constraints = [dominio('tipo',['STATUS','EVIDENCIA','ALERTA'],'entrega_tipo_valido'),
            preenchido('chave','entrega_chave_preenchida'), objeto('conteudo','entrega_conteudo_objeto')]


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
        constraints = [dominio('cenario',['livre','proximidade','desmatamento','nuvens','fonte_indisponivel','vencido'],
            'cenario_tipo_valido'), objeto('dados','cenario_dados_objeto')]


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
        constraints = [dominio('perfil_voo',['valido','cobertura_insuficiente','antigo','sem_georreferencia'],'upload_perfil_valido'),
            dominio('status',['EM_ENVIO','VALIDADO','REJEITADO','CANCELADO'],'upload_status_valido'),
            sha256('poligono_sha256','upload_sha256_valido'), objeto('cobertura','upload_cobertura_objeto',True),
            objeto('partes','upload_partes_objeto'), objeto('validacao','upload_validacao_objeto'),
            models.CheckConstraint(condition=models.Q(tamanho_declarado__gt=0,total_partes__gt=0,total_partes__lte=10000),
                name='upload_tamanho_partes_validos')]
