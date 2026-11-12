import csv
import io
import uuid
from functools import wraps
from xml.sax.saxutils import escape

from django.db.models import Count,F,Sum
from django.http import HttpResponse,JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET,require_POST

from .acesso import capacidades,perfil,permite,PERFIS
from .models import CenarioSimulado,EntregaCloud,Talhao,UploadSimulado
from .portal import body
from .simulacao import CENARIOS,PERFIS_VOO,criar,iniciar_voo,enviar_parte,concluir_voo

def contract(view):
    @wraps(view)
    def wrapped(*args,**kwargs):
        try:return view(*args,**kwargs)
        except (ValueError,TypeError) as exc:return JsonResponse({'detalhe':str(exc)},status=400)
    return wrapped

def voo_json(row):
    return {'id':str(row.pk),'vistoria':row.vistoria_id,'perfil':row.perfil_voo,'data_voo':str(row.data_voo),
        'status':row.status,'cobertura':row.cobertura,'tamanho_declarado':row.tamanho_declarado,
        'bytes_reais_transferidos':0,'partes':sorted(int(x) for x in row.partes),'total_partes':row.total_partes,
        'validacao':row.validacao,'url':f'/app/laboratorio/voos/{row.pk}/desenho/'}

@permite('consultar')
@require_GET
def estado(request):
    rows=CenarioSimulado.objects.select_related('talhao').prefetch_related('uploads')[:60]
    return JsonResponse({'simulado':True,'perfil':perfil(request.user),'capacidades':sorted(capacidades(request.user)),
        'perfis':{k:sorted(v) for k,v in PERFIS.items()},
        'cenarios':[{'id':k,'nome':v[0],'descricao':v[1]} for k,v in CENARIOS.items()],
        'execucoes':[{'id':str(r.pk),'cenario':r.cenario,'talhao':r.talhao_id,'codigo':r.talhao.codigo,
            'status':r.talhao.status,'criado_em':r.criado_em.isoformat(),'dados':r.dados,
            'uploads':[voo_json(u) for u in r.uploads.all()]} for r in rows]})

@permite('laboratorio')
@require_POST
@contract
def executar(request):
    data=body(request)
    if not data:raise ValueError('Informe o cenário em JSON.')
    row=criar(data.get('cenario'),request.user,data.get('idempotencia'))
    return JsonResponse({'id':str(row.pk),'talhao':row.talhao_id,'simulado':True},status=201)

@permite('campo')
@require_POST
@contract
def iniciar(request,pk):
    row=get_object_or_404(CenarioSimulado,pk=pk);data=body(request) or {}
    return JsonResponse(voo_json(iniciar_voo(row,data.get('perfil','valido'),request.user)),status=201)

@permite('campo')
@require_POST
@contract
def parte(request,pk):
    get_object_or_404(UploadSimulado,pk=pk)
    return JsonResponse(voo_json(enviar_parte(pk,(body(request) or {}).get('parte'))))

@permite('campo')
@require_POST
@contract
def finalizar(request,pk):
    get_object_or_404(UploadSimulado,pk=pk)
    return JsonResponse(voo_json(concluir_voo(pk,request.user)))

@permite('campo')
@require_POST
def cancelar(request,pk):
    from django.db import transaction
    from .simulacao import evento
    with transaction.atomic():
        row=get_object_or_404(UploadSimulado.objects.select_for_update(),pk=pk)
        if row.status!='EM_ENVIO':return JsonResponse({'detalhe':'O envio já foi encerrado.'},status=409)
        row.status='CANCELADO';row.save(update_fields=['status'])
        evento(request.user,'CANCELAR_ENVIO_SIMULADO',row.cenario.talhao,'envio virtual cancelado',{'upload':str(row.pk)})
    return JsonResponse(voo_json(row))

@permite('consultar')
@require_GET
def desenho(request,pk):
    row=get_object_or_404(UploadSimulado.objects.select_related('cenario__talhao'),pk=pk)
    from .ambiental import geometry
    from .simulacao import CENARIOS
    from .models import AnaliseAmbiental
    snapshot=row.validacao.get('manifesto',{}).get('poligono')
    if not snapshot:snapshot=AnaliseAmbiental.objects.get(pk=row.cenario.dados['analise']).poligono
    shape=geometry(snapshot);a,b,c,d=shape.bounds
    def path(value):
        from .ambiental import geometry
        geom=geometry(value)
        polygons=[geom] if geom.geom_type=='Polygon' else list(geom.geoms)
        return ' '.join(' '.join(('M' if i==0 else 'L')+str(round(60+(x-a)/(c-a)*580,2))+','+
            str(round(350-(y-b)/(d-b)*230,2)) for i,(x,y,*_) in enumerate(poly.exterior.coords))+' Z' for poly in polygons)
    coverage=f'<path d="{path(row.cobertura)}" fill="#94b6a2" fill-opacity=".6"/>' if row.cobertura else ''
    content=f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 700 430"><rect width="700" height="430" fill="#f6f7f2"/>
    <text x="35" y="38" font-family="sans-serif" font-size="19" fill="#183e2c">Voo virtual Raízes · SIMULAÇÃO</text>
    <text x="35" y="68" font-family="sans-serif" font-size="12">Representação geométrica. Nenhuma imagem de drone real foi capturada.</text>
    {coverage}<path d="{path(snapshot)}" fill="none" stroke="#183e2c" stroke-width="3"/>
    <text x="35" y="393" font-family="sans-serif" font-size="12">Cobertura: {row.validacao.get('cobertura_percentual','pendente')}% · {escape(row.status)} · {row.data_voo}</text></svg>'''
    response=HttpResponse(content,content_type='image/svg+xml')
    response['Content-Disposition']=f'inline; filename="voo-virtual-{row.pk}.svg"'
    response['Content-Security-Policy']="default-src 'none'; style-src 'unsafe-inline'"
    return response

def report_rows():
    result=[]
    for simulated in [False,True]:
        rows=Talhao.objects.filter(cenario_simulado__isnull=not simulated).values(
            municipio=F('fazenda__municipio')).values('municipio','status').annotate(talhoes=Count('id'),area_ha=Sum('area_ha')).order_by('municipio','status')
        result.extend({'ambiente':'SIMULACAO' if simulated else 'OPERACIONAL',**row} for row in rows)
    return result

@permite('consultar')
@require_GET
def relatorios(request):
    deliveries=EntregaCloud.objects.order_by('-id')[:50]
    return JsonResponse({'motor':'PostgreSQL (Athena permanece arquitetura-alvo)', 'linhas':report_rows(),
        'entregas':[{'id':e.pk,'tipo':e.tipo,'chave':e.chave,'tentativas':e.tentativas,
            'estado':'ENVIADO' if e.enviado_em else 'PENDENTE','erro':e.erro,'criado_em':e.criado_em.isoformat()} for e in deliveries]})

@permite('exportar')
@require_GET
def exportar_csv(request):
    from .models import EventoAuditoria
    text=io.StringIO();writer=csv.DictWriter(text,fieldnames=['ambiente','municipio','status','talhoes','area_ha'],delimiter=';')
    writer.writeheader();writer.writerows(report_rows())
    EventoAuditoria.objects.create(ator=request.user,acao='EXPORTAR_RELATORIO',recurso='relatorio',
        descricao='Relatório analítico exportado; dados operacionais e simulados identificados')
    response=HttpResponse('\ufeff'+text.getvalue(),content_type='text/csv; charset=utf-8')
    response['Content-Disposition']='attachment; filename="raizes-relatorio.csv"'
    return response
