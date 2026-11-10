from decimal import Decimal

from rest_framework import serializers

from .models import Fazenda, Lote, LoteTalhao, Produtor, Talhao


class TalhaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Talhao
        fields = "__all__"


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
