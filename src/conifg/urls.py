from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from lavouraInteligente.views import (
    FazendaViewSet,
    LoteTalhaoViewSet,
    LoteViewSet,
    ProdutorViewSet,
    TalhaoViewSet,
)

router = DefaultRouter()
router.register("produtores", ProdutorViewSet)
router.register("fazendas", FazendaViewSet)
router.register("talhoes", TalhaoViewSet, basename="talhao")
router.register("lotes", LoteViewSet)
router.register("lote-itens", LoteTalhaoViewSet)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include(router.urls)),
]
