from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter
from django.contrib.auth import views as auth_views
from lavouraInteligente import portal

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
    path('', portal.home, name='home'),
    path('entrar/', auth_views.LoginView.as_view(template_name='raizes/login.html'), name='login'),
    path('sair/', auth_views.LogoutView.as_view(), name='logout'),
    path('app/estado/', portal.estado, name='portal_estado'),
    path('app/integracoes/', portal.integracoes),
    path('app/analises/<int:pk>/', portal.evidencia_ambiental),
    path('app/talhoes/<int:pk>/analisar/', portal.analisar_ambiental),
    path('app/talhoes/<int:pk>/revisar/', portal.revisar, name='portal_revisar'),
    path('app/talhoes/<int:pk>/vistoria/', portal.solicitar_vistoria, name='portal_vistoria'),
    path('app/lotes/<int:pk>/decisao/', portal.decidir, name='portal_decisao'),
    path('app/vistorias/<int:pk>/status/', portal.atualizar_vistoria),
    path('app/vistorias/<int:pk>/arquivo/', portal.enviar_arquivo),
    path('app/arquivos/<int:pk>/', portal.baixar_arquivo),
    path('app/exportar/<str:tipo>/<int:pk>/', portal.exportar),
    path("admin/", admin.site.urls),
    path("api/", include(router.urls)),
]
