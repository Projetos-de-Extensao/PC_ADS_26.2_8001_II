from rest_framework import viewsets
from .models import lavouraInteligente
from .serializers import lavouraInteligenteSerializer


class lavouraInteligenteViewSet(viewsets.ModelViewSet):
    queryset = lavouraInteligente.objects.all().order_by("-criada_em")
    serializer_class = lavouraInteligenteSerializer