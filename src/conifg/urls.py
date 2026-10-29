from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter
from lavouraInteligente.views import lavouraInteligenteViewSet

router = DefaultRouter()
router.register("lavouras", lavouraInteligenteViewSet)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include(router.urls)),
]