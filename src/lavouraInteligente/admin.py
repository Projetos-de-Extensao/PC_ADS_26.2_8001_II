from django.contrib import admin

from .models import Fazenda, Lote, LoteTalhao, Produtor, Talhao


class FazendaInline(admin.TabularInline):
    model = Fazenda
    extra = 0


class TalhaoInline(admin.TabularInline):
    model = Talhao
    extra = 0
    fields = ["codigo", "cultura", "area_ha", "status"]


class LoteTalhaoInline(admin.TabularInline):
    model = LoteTalhao
    extra = 0


@admin.register(Produtor)
class ProdutorAdmin(admin.ModelAdmin):
    list_display = ["nome", "documento", "municipio", "uf"]
    search_fields = ["nome", "documento"]
    inlines = [FazendaInline]


@admin.register(Fazenda)
class FazendaAdmin(admin.ModelAdmin):
    list_display = ["nome", "produtor", "municipio", "uf", "area_ha"]
    list_filter = ["uf"]
    search_fields = ["nome", "car_codigo"]
    inlines = [TalhaoInline]


@admin.register(Talhao)
class TalhaoAdmin(admin.ModelAdmin):
    list_display = ["codigo", "fazenda", "cultura", "area_ha", "status", "atualizado_em"]
    list_filter = ["status", "cultura"]
    search_fields = ["codigo"]


@admin.register(Lote)
class LoteAdmin(admin.ModelAdmin):
    list_display = ["codigo", "recebido_em", "peso_total_kg", "status"]
    list_filter = ["status"]
    inlines = [LoteTalhaoInline]


@admin.register(LoteTalhao)
class LoteTalhaoAdmin(admin.ModelAdmin):
    list_display = ["lote", "talhao", "peso_kg"]
