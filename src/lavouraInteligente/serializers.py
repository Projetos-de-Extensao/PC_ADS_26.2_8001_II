from decimal import Decimal

from rest_framework import serializers

from .models import Fazenda, Lote, LoteTalhao, Produtor, Talhao


class TalhaoSerializer(serializers.ModelSerializer):
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
        return value

    class Meta:
        model = Talhao
        fields = "__all__"
        read_only_fields = ['status']


class FazendaSerializer(serializers.ModelSerializer):
    talhoes = TalhaoSerializer(many=True, read_only=True)

    class Meta:
        model = Fazenda
        fields = "__all__"


class ProdutorSerializer(serializers.ModelSerializer):
    fazendas = FazendaSerializer(many=True, read_only=True)

    class Meta:
        model = Produtor
        fields = "__all__"


class LoteTalhaoSerializer(serializers.ModelSerializer):
    talhao_codigo = serializers.CharField(source="talhao.codigo", read_only=True)

    class Meta:
        model = LoteTalhao
        fields = ["id", "lote", "talhao", "talhao_codigo", "peso_kg"]


class LoteSerializer(serializers.ModelSerializer):
    itens = LoteTalhaoSerializer(many=True, read_only=True)

    class Meta:
        model = Lote
        fields = ["id", "codigo", "recebido_em", "peso_total_kg", "status", "motivo", "itens"]


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
