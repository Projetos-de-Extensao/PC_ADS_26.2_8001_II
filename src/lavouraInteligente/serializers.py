from decimal import Decimal

from rest_framework import serializers

from .models import Fazenda, Lote, LoteTalhao, Produtor, Talhao
from .validacao import normalizar_documento, validar_documento, formatar_documento, DOCUMENTO_DEMO, UFS
from django.core.exceptions import ValidationError as DjangoValidationError


class CadastroValidadoSerializer(serializers.ModelSerializer):
    def validate(self, data):
        for name, value in data.items():
            field = self.Meta.model._meta.get_field(name)
            if isinstance(value, str) and not field.blank and not value.strip():
                raise serializers.ValidationError({name:'Este campo é obrigatório.'})
        return super().validate(data)

    def to_internal_value(self, data):
        data = data.copy()
        if isinstance(data.get('uf'), str):
            data['uf'] = data['uf'].strip().upper()
        return super().to_internal_value(data)


class TalhaoSerializer(CadastroValidadoSerializer):
    def create(self,validated_data):
        validated_data['status']='REVISAO'
        return super().create(validated_data)

    def update(self,instance,validated_data):
        if 'poligono' in validated_data and validated_data['poligono']!=instance.poligono:
            validated_data['status']='BLOQUEADO' if instance.status=='BLOQUEADO' else 'REVISAO'
        return super().update(instance,validated_data)

    def validate_atributos(self,value):
        if not isinstance(value,dict):
            raise serializers.ValidationError('Os atributos devem ser um objeto JSON.')
        previous=self.instance.atributos.get('analise_ambiental') if self.instance else None
        if value.get('analise_ambiental')!=previous:
            raise serializers.ValidationError('A análise ambiental é gerenciada pelo sistema; use a ação Consultar INPE.')
        for key in ['ambiente','simulacao']:
            previous=self.instance.atributos.get(key) if self.instance else None
            if value.get(key)!=previous:raise serializers.ValidationError('A identificação de simulação é gerenciada pelo laboratório.')
        return value

    def validate_poligono(self,value):
        if value=={}: return value
        if not isinstance(value,dict) or value.get('type') not in ('Polygon','MultiPolygon'):
            raise serializers.ValidationError('Use uma geometria GeoJSON Polygon ou MultiPolygon.')
        coords=value.get('coordinates')
        if not isinstance(coords,list) or not coords:
            raise serializers.ValidationError('Informe as coordenadas da geometria.')
        polygons=[coords] if value['type']=='Polygon' else coords
        count=0
        for polygon in polygons:
            if not isinstance(polygon,list) or not polygon:
                raise serializers.ValidationError('O polígono não possui anel externo.')
            for ring in polygon:
                if not isinstance(ring,list) or len(ring)<4 or ring[0]!=ring[-1]:
                    raise serializers.ValidationError('Cada anel deve ser fechado e possuir pelo menos quatro coordenadas.')
                count+=len(ring)
                for point in ring:
                    if (not isinstance(point,list) or len(point)<2 or
                        not all(isinstance(v,(int,float)) and not isinstance(v,bool) for v in point[:2]) or
                        not -74<=point[0]<=-34 or not -34<=point[1]<=6):
                        raise serializers.ValidationError('Informe coordenadas WGS84 no Brasil: longitude, latitude.')
        if count>2000:raise serializers.ValidationError('A geometria ultrapassa o limite de 2.000 vértices.')
        from .ambiental import geometry
        try:
            geometry(value)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc))
        return value

    class Meta:
        model = Talhao
        fields = "__all__"
        read_only_fields = ['status']


class FazendaSerializer(CadastroValidadoSerializer):
    talhoes = TalhaoSerializer(many=True, read_only=True)

    class Meta:
        model = Fazenda
        fields = "__all__"


class ProdutorSerializer(CadastroValidadoSerializer):
    documento = serializers.CharField(max_length=18)
    documento_formatado = serializers.SerializerMethodField()
    fazendas = FazendaSerializer(many=True, read_only=True)

    def get_documento_formatado(self, obj):
        return formatar_documento(obj.documento)

    def validate_documento(self, value):
        try:
            value = normalizar_documento(value)
            if self.instance and self.instance.simulado and value == DOCUMENTO_DEMO:
                return value
            validar_documento(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages)
        query = Produtor.objects.filter(documento=value)
        if self.instance:
            query = query.exclude(pk=self.instance.pk)
        if query.exists():
            raise serializers.ValidationError('Já existe um produtor com este CPF/CNPJ, com ou sem pontuação.')
        return value

    class Meta:
        model = Produtor
        fields = "__all__"
        read_only_fields = ['simulado']


class LoteTalhaoSerializer(CadastroValidadoSerializer):
    talhao_codigo = serializers.CharField(source="talhao.codigo", read_only=True)

    def validate(self,data):
        lote=data.get('lote',self.instance.lote if self.instance else None)
        talhao=data.get('talhao',self.instance.talhao if self.instance else None)
        if lote and hasattr(lote,'decisao'):
            raise serializers.ValidationError('Lote com decisão registrada não permite alterar origens.')
        if lote and talhao:
            from .models import CenarioSimulado
            simulated=CenarioSimulado.objects.filter(talhao=talhao).exists()
            others=lote.itens.exclude(pk=self.instance.pk if self.instance else None)
            for item in others.select_related('talhao'):
                if CenarioSimulado.objects.filter(talhao=item.talhao).exists()!=simulated:
                    raise serializers.ValidationError('Não misture origens simuladas e operacionais.')
        return data

    class Meta:
        model = LoteTalhao
        fields = ["id", "lote", "talhao", "talhao_codigo", "peso_kg"]


class LoteSerializer(CadastroValidadoSerializer):
    itens = LoteTalhaoSerializer(many=True, read_only=True)
    simulado = serializers.SerializerMethodField()

    def get_simulado(self,obj):
        return obj.itens.filter(talhao__cenario_simulado__isnull=False).exists()

    class Meta:
        model = Lote
        fields = ["id", "codigo", "recebido_em", "peso_total_kg", "status", "motivo", "itens", "simulado"]


class ItemRecebimentoSerializer(serializers.Serializer):
    talhao = serializers.PrimaryKeyRelatedField(queryset=Talhao.objects.all())
    peso_kg = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"))


class RecebimentoSerializer(serializers.Serializer):
    """Entrada do endpoint transacional de recebimento de lote na balança."""

    codigo = serializers.CharField(max_length=40)
    peso_total_kg = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"))
    itens = ItemRecebimentoSerializer(many=True, allow_empty=False)

    def validate_codigo(self, value):
        if Lote.objects.filter(codigo=value).exists():
            raise serializers.ValidationError("Já existe um lote com este código.")
        return value
