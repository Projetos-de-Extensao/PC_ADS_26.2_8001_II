from rest_framework import serializers
from .models import lavouraInteligente



class lavouraInteligenteSerializer(serializers.ModelSerializer):
    class Meta:
        model = lavouraInteligente
        fields = "__all__"