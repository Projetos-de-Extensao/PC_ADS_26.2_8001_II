"""Interface operacional Raízes e ações com autoria, justificativa e CSRF."""
import hashlib
import io
import json
import zipfile
from datetime import date
from functools import wraps

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import FileResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST

from .models import (ArquivoVistoria, DecisaoRecebimento, EventoAuditoria, Fazenda,
                     Lote, Produtor, RevisaoStatus, StatusRisco, Talhao, Vistoria)
from .serializers import (FazendaSerializer, LoteSerializer, ProdutorSerializer, TalhaoSerializer)
from .acesso import permite,capacidades,perfil


@login_required
@require_GET
def evidencia_ambiental(request,pk):
    if not request.user.is_staff:return JsonResponse({'detalhe':'Acesso restrito à equipe.'},status=403)
    from .models import AnaliseAmbiental
    a=get_object_or_404(AnaliseAmbiental,pk=pk)
    data={'id':a.id,'talhao':a.talhao_id,'poligono':a.poligono,'poligono_sha256':a.poligono_sha256,
        'resultado':a.resultado,'datasets':a.datasets,'criado_em':a.criado_em.isoformat(),
        'valido_ate':a.valido_ate.isoformat()}
    response=JsonResponse(data,json_dumps_params={'ensure_ascii':False,'indent':2})
    response['Content-Disposition']=f'attachment; filename="raizes-analise-{a.id}.json"'
    return response


@login_required
@require_GET
def integracoes(request):
    if not request.user.is_staff:
        return JsonResponse({'detalhe':'Acesso restrito à equipe.'},status=403)
    from .cloud import configured
    from .models import AnaliseAmbiental, EntregaCloud
    return JsonResponse({'aws_configurada':configured(),
        'cloud_pendentes':EntregaCloud.objects.filter(enviado_em__isnull=True).count(),
        'cloud_entregues':EntregaCloud.objects.filter(enviado_em__isnull=False).count(),
        'analises':[{'id':a.id,'talhao':a.talhao_id,'codigo':a.talhao.codigo,'status':a.status,
            'criado_em':a.criado_em.isoformat(),'valido_ate':a.valido_ate.isoformat(),
            'poligono_sha256':a.poligono_sha256,'resultado':a.resultado}
            for a in AnaliseAmbiental.objects.select_related('talhao')[:100]],
        'fontes':[{'nome':'INPE/DETER Amazônia e Cerrado','situacao':'Consulta pública integrada'},
            {'nome':'MapBiomas Alerta','situacao':'Credencial e contrato de dados pendentes'},
            {'nome':'Sentinel/Copernicus','situacao':'Integração de imagens e análise espectral pendentes'}]})


@login_required
@require_POST
@permite('analise')
def analisar_ambiental(request,pk):
    if not request.user.is_staff:
        return JsonResponse({'detalhe':'Acesso restrito à equipe.'},status=403)
    from .ambiental import analyze
    get_object_or_404(Talhao,pk=pk)
    from .models import CenarioSimulado
    if CenarioSimulado.objects.filter(talhao_id=pk).exists():
        return JsonResponse({'detalhe':'Este talhão pertence ao laboratório. As consultas reais permanecem separadas dos cenários virtuais.'},status=409)
    # Short-lived PostgreSQL advisory lock prevents parallel analyses without holding a
    # database row transaction open during the external HTTP requests.
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute('SELECT pg_try_advisory_lock(%s,%s)',[7241,pk])
        acquired=cursor.fetchone()[0]
    if not acquired:return JsonResponse({'detalhe':'Já há uma análise em andamento para este talhão.'},status=409)
    try:
        from .models import AnaliseAmbiental
        from datetime import timedelta
        if AnaliseAmbiental.objects.filter(talhao_id=pk,criado_em__gte=timezone.now()-timedelta(minutes=5)).exists():
            return JsonResponse({'detalhe':'Aguarde cinco minutos antes de consultar novamente esta origem.'},status=429)
        row=analyze(pk,request.user)
        return JsonResponse({'id':row.id,'status':row.status,'resultado':row.resultado},status=201)
    except ValueError as exc:return JsonResponse({'detalhe':str(exc)},status=409)
    finally:
        with connection.cursor() as cursor:cursor.execute('SELECT pg_advisory_unlock(%s,%s)',[7241,pk])


def equipe(view):
    @wraps(view)
    @login_required
    def protected(request,*args,**kwargs):
        if not request.user.is_staff:
            return JsonResponse({'detalhe':'Acesso restrito à equipe autorizada.'},status=403)
        return view(request,*args,**kwargs)
    return protected


def body(request):
    try:
        value=json.loads(request.body)
        if not isinstance(value,dict): raise ValueError()
        return value
    except (ValueError,UnicodeError):
        return None


def evento(request,acao,recurso,pk,descricao,dados=None):
    return EventoAuditoria.objects.create(ator=request.user,acao=acao,recurso=recurso,
        recurso_id=pk,descricao=descricao,dados=dados or {})


@equipe
@ensure_csrf_cookie
def home(request):
    return render(request,'raizes/portal.html')


@equipe
@require_GET
def estado(request):
    vistorias=[]
    for v in Vistoria.objects.select_related('talhao','solicitante').prefetch_related('arquivos'):
        vistorias.append({'id':v.id,'talhao':v.talhao_id,'codigo':v.talhao.codigo,'motivo':v.motivo,
          'prazo':v.prazo.isoformat(),'status':v.status,'criado_em':v.criado_em.isoformat(),
          'solicitante':v.solicitante.get_username() if v.solicitante else 'Usuário removido',
          'arquivos':[{'id':a.id,'nome':a.nome_original,'sha256':a.sha256,'tamanho':a.tamanho,
            'url':f'/app/arquivos/{a.id}/'} for a in v.arquivos.all()]})
    decisoes={d.lote_id:{'acao':d.acao,'justificativa':d.justificativa,
        'operador':d.operador.get_username() if d.operador else 'Usuário removido',
        'criado_em':d.criado_em.isoformat()} for d in DecisaoRecebimento.objects.select_related('operador')}
    historico=[{'id':e.id,'acao':e.acao,'recurso':e.recurso,'recurso_id':e.recurso_id,
        'descricao':e.descricao,'dados':e.dados,'criado_em':e.criado_em.isoformat(),
        'ator':e.ator.get_username() if e.ator else 'API acadêmica'}
        for e in EventoAuditoria.objects.select_related('ator')[:500]]
    return JsonResponse({'usuario':{'nome':request.user.get_full_name() or request.user.get_username(),
        'perfil':perfil(request.user),'capacidades':sorted(capacidades(request.user))},
        'produtores':ProdutorSerializer(Produtor.objects.prefetch_related('fazendas__talhoes'),many=True).data,
        'fazendas':FazendaSerializer(Fazenda.objects.select_related('produtor').prefetch_related('talhoes'),many=True).data,
        'talhoes':TalhaoSerializer(Talhao.objects.select_related('fazenda'),many=True).data,
        'lotes':LoteSerializer(Lote.objects.prefetch_related('itens__talhao'),many=True).data,
        'vistorias':vistorias,'decisoes':decisoes,'historico':historico,
        'atualizado_em':timezone.now().isoformat()})


@equipe
@require_POST
@transaction.atomic
@permite('analise')
def revisar(request,pk):
    dados=body(request)
    if dados is None:return JsonResponse({'detalhe':'JSON inválido.'},status=400)
    justificativa=str(dados.get('justificativa','')).strip()
    status=dados.get('status')
    if status not in StatusRisco.values or len(justificativa)<10:
        return JsonResponse({'detalhe':'Informe um status válido e uma justificativa com pelo menos 10 caracteres.'},status=400)
    talhao=get_object_or_404(Talhao.objects.select_for_update(),pk=pk)
    if talhao.status not in (StatusRisco.REVISAO,StatusRisco.BLOQUEADO):
        return JsonResponse({'detalhe':'A revisão humana é destinada a talhões em REVISÃO ou BLOQUEADO.'},status=409)
    if status==StatusRisco.APROVADO and not talhao.poligono:
        return JsonResponse({'detalhe':'Cadastre um polígono antes de aprovar a origem.'},status=409)
    if status==StatusRisco.APROVADO:
        from .models import CenarioSimulado,UploadSimulado
        from .ambiental import canonical
        run=CenarioSimulado.objects.filter(talhao=talhao).first()
        if run and run.cenario in ['proximidade','nuvens']:
            digest=hashlib.sha256(canonical(talhao.poligono)).hexdigest()
            if not UploadSimulado.objects.filter(cenario=run,status='VALIDADO',poligono_sha256=digest).exists():
                return JsonResponse({'detalhe':'Neste cenário, conclua um voo virtual válido antes da revisão de aprovação.'},status=409)
    revisao=RevisaoStatus.objects.create(talhao=talhao,autor=request.user,
       status_anterior=talhao.status,status_novo=status,justificativa=justificativa,
       evidencia_original={'status':talhao.status,'atributos':talhao.atributos,'poligono':talhao.poligono})
    talhao.status=status
    talhao.save(update_fields=['status','atualizado_em'])
    evento(request,'REVISAR_STATUS','talhao',talhao.id,f'{talhao.codigo}: revisão de status',
           {'de':revisao.status_anterior,'para':status,'justificativa':justificativa})
    return JsonResponse({'id':revisao.id,'status':status},status=201)


@equipe
@require_POST
@transaction.atomic
@permite('balanca')
def decidir(request,pk):
    dados=body(request)
    if dados is None:return JsonResponse({'detalhe':'JSON inválido.'},status=400)
    lote=get_object_or_404(Lote.objects.select_for_update(),pk=pk)
    acao=dados.get('acao')
    justificativa=str(dados.get('justificativa','')).strip()
    if acao not in ('ACEITAR','RECUSAR') or len(justificativa)<10:
        return JsonResponse({'detalhe':'Escolha aceitar/recusar e registre uma justificativa com pelo menos 10 caracteres.'},status=400)
    if acao=='ACEITAR' and lote.status!=StatusRisco.APROVADO:
        return JsonResponse({'detalhe':'Um lote em revisão ou bloqueado não pode ser aceito sem regularização das origens.'},status=409)
    if acao=='ACEITAR' and not lote.itens.exists():
        return JsonResponse({'detalhe':'Vincule os talhões de origem antes de aceitar o recebimento.'},status=409)
    if acao=='ACEITAR':
        from django.db.models import Sum
        if lote.itens.aggregate(total=Sum('peso_kg'))['total'] != lote.peso_total_kg:
            return JsonResponse({'detalhe':'A soma dos pesos das origens deve ser igual ao peso total do lote.'},status=409)
        from .risco import status_efetivo
        origins=Talhao.objects.select_for_update().filter(entregas__lote=lote).order_by('pk')
        if any(status_efetivo(t)!='APROVADO' for t in origins):
            return JsonResponse({'detalhe':'Uma origem mudou de risco, está vencida ou possui geometria inválida. Reavalie os talhões antes de aceitar.'},status=409)
        from .models import CenarioSimulado
        ids=list(lote.itens.values_list('talhao_id',flat=True))
        simulated=CenarioSimulado.objects.filter(talhao_id__in=ids).count()
        if simulated not in (0,len(ids)):
            return JsonResponse({'detalhe':'Origens simuladas e operacionais não podem compor o mesmo lote.'},status=409)
    if DecisaoRecebimento.objects.filter(lote=lote).exists():
        return JsonResponse({'detalhe':'A decisão deste lote já foi registrada e preservada para auditoria.'},status=409)
    decisao=DecisaoRecebimento.objects.create(lote=lote,operador=request.user,acao=acao,
        status_consultado=lote.status,justificativa=justificativa)
    evento(request,'DECISAO_BALANCA','lote',lote.id,f'{lote.codigo}: '+('recebimento aceito' if acao=='ACEITAR' else 'recebimento recusado'),
        {'acao':acao,'status_consultado':lote.status,'justificativa':justificativa})
    return JsonResponse({'id':decisao.id,'acao':acao},status=201)


@equipe
@require_POST
@transaction.atomic
@permite('analise')
def solicitar_vistoria(request,pk):
    dados=body(request)
    if dados is None:return JsonResponse({'detalhe':'JSON inválido.'},status=400)
    talhao=get_object_or_404(Talhao.objects.select_for_update(),pk=pk)
    motivo=str(dados.get('motivo','')).strip()
    try:prazo=date.fromisoformat(dados.get('prazo',''))
    except (ValueError,TypeError):return JsonResponse({'detalhe':'Informe um prazo válido.'},status=400)
    if talhao.status!=StatusRisco.REVISAO:
        return JsonResponse({'detalhe':'Somente talhões em REVISÃO podem receber solicitação de vistoria.'},status=409)
    if len(motivo)<10 or prazo<timezone.localdate():
        return JsonResponse({'detalhe':'Informe motivo com pelo menos 10 caracteres e prazo de hoje em diante.'},status=400)
    existente=Vistoria.objects.filter(talhao=talhao,status__in=['SOLICITADA','AGENDADA']).first()
    if existente:return JsonResponse({'id':existente.id,'existente':True})
    vistoria=Vistoria.objects.create(talhao=talhao,solicitante=request.user,motivo=motivo,prazo=prazo)
    evento(request,'SOLICITAR_VISTORIA','talhao',pk,f'{talhao.codigo}: vistoria solicitada',{'vistoria':vistoria.id,'motivo':motivo,'prazo':str(prazo)})
    return JsonResponse({'id':vistoria.id},status=201)


@equipe
@require_POST
@transaction.atomic
@permite('campo')
def atualizar_vistoria(request,pk):
    dados=body(request)
    vistoria=get_object_or_404(Vistoria.objects.select_for_update(),pk=pk)
    if not dados or dados.get('status')!='AGENDADA' or vistoria.status!='SOLICITADA':
        return JsonResponse({'detalhe':'Apenas uma vistoria solicitada pode ser marcada como agendada.'},status=409)
    vistoria.status='AGENDADA';vistoria.save(update_fields=['status'])
    evento(request,'AGENDAR_VISTORIA','talhao',vistoria.talhao_id,f'{vistoria.talhao.codigo}: vistoria agendada',{'vistoria':vistoria.id})
    return JsonResponse({'status':vistoria.status})


@equipe
@require_POST
@transaction.atomic
@permite('campo')
def enviar_arquivo(request,pk):
    vistoria=get_object_or_404(Vistoria.objects.select_for_update(),pk=pk)
    arquivo=request.FILES.get('arquivo')
    if not arquivo or arquivo.size>20*1024*1024:
        return JsonResponse({'detalhe':'Envie uma imagem de até 20 MB nesta implantação.'},status=400)
    from PIL import Image,UnidentifiedImageError
    try:
        image=Image.open(arquivo)
        if image.format not in ('JPEG','PNG','TIFF'):raise ValueError()
        image.verify()
    except (UnidentifiedImageError,ValueError,OSError,Image.DecompressionBombError):
        return JsonResponse({'detalhe':'Arquivo inválido. Use uma imagem JPEG, PNG ou TIFF íntegra.'},status=400)
    arquivo.seek(0);digest=hashlib.sha256()
    for chunk in arquivo.chunks():digest.update(chunk)
    arquivo.seek(0)
    anexo=ArquivoVistoria.objects.create(vistoria=vistoria,arquivo=arquivo,nome_original=arquivo.name,
       tamanho=arquivo.size,sha256=digest.hexdigest(),autor=request.user)
    vistoria.status='RECEBIDA';vistoria.save(update_fields=['status'])
    evento(request,'RECEBER_IMAGEM','talhao',vistoria.talhao_id,f'{vistoria.talhao.codigo}: imagem de vistoria recebida',
           {'vistoria':vistoria.id,'sha256':anexo.sha256,'arquivo':anexo.nome_original,
            'validacao_geoespacial':'pendente; recebimento não aprova a evidência'})
    return JsonResponse({'id':anexo.id,'sha256':anexo.sha256,'status':'RECEBIDA'},status=201)


@equipe
@require_GET
def baixar_arquivo(request,pk):
    arquivo=get_object_or_404(ArquivoVistoria,pk=pk)
    return FileResponse(arquivo.arquivo.open('rb'),as_attachment=True,filename=arquivo.nome_original)


@equipe
@require_GET
@permite('exportar')
def exportar(request,tipo,pk):
    if tipo=='talhao':
        obj=get_object_or_404(Talhao,pk=pk)
        payload={'talhao':TalhaoSerializer(obj).data,'revisoes':list(obj.revisoes.values('status_anterior','status_novo','justificativa','evidencia_original','criado_em'))}
    elif tipo=='lote':
        obj=get_object_or_404(Lote.objects.prefetch_related('itens__talhao'),pk=pk)
        payload={'lote':LoteSerializer(obj).data,'origens':TalhaoSerializer(obj.talhoes.all(),many=True).data,
            'decisao':list(DecisaoRecebimento.objects.filter(lote=obj).values('acao','status_consultado','justificativa','criado_em'))}
    else:return JsonResponse({'detalhe':'Recurso inválido.'},status=404)
    from django.core.serializers.json import DjangoJSONEncoder
    raw=json.dumps(payload,cls=DjangoJSONEncoder,ensure_ascii=False,sort_keys=True,indent=2).encode()
    buffer=io.BytesIO()
    with zipfile.ZipFile(buffer,'w',zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('registro.json',raw)
        from .models import CenarioSimulado
        plots=[obj] if tipo=='talhao' else list(obj.talhoes.all())
        files={}
        for plot in plots:
            files[f'geometrias/talhao-{plot.pk}.geojson']=plot.poligono
            for a in plot.analises.order_by('id')[:100]:
                files[f'analises/{a.pk}.json']={'poligono_sha256':a.poligono_sha256,'resultado':a.resultado,
                    'datasets':a.datasets,'criado_em':a.criado_em,'valido_ate':a.valido_ate}
            files[f'auditoria/talhao-{plot.pk}.json']=list(EventoAuditoria.objects.filter(recurso='talhao',recurso_id=plot.pk).values(
                'id','acao','ator_id','descricao','dados','criado_em')[:500])
            run=CenarioSimulado.objects.filter(talhao=plot).first()
            if run:
                for upload in run.uploads.all():files[f'vistorias-simuladas/{upload.pk}.json']=upload.validacao or {
                    'simulado':True,'estado':upload.status,'partes_recebidas':len(upload.partes),'bytes_reais_transferidos':0}
        hashes={'registro.json':hashlib.sha256(raw).hexdigest()}
        for name,value in files.items():
            content=json.dumps(value,cls=DjangoJSONEncoder,ensure_ascii=False,sort_keys=True,indent=2).encode()
            archive.writestr(name,content);hashes[name]=hashlib.sha256(content).hexdigest()
        archive.writestr('manifesto.json',json.dumps({'sha256':hashlib.sha256(raw).hexdigest(),
            'arquivos':hashes,'simulado':any(CenarioSimulado.objects.filter(talhao=plot).exists() for plot in plots),
            'recurso':tipo,'id':pk,'gerado_em':timezone.now().isoformat(),
            'escopo':'Dossiê acadêmico: registro, geometrias, análises, auditoria e metadados de voos virtuais disponíveis. Não é certificação jurídica, não inclui todos os arquivos de imagem nem garante cinco anos de retenção.'},ensure_ascii=False,indent=2))
    evento(request,'EXPORTAR_REGISTRO',tipo,pk,f'{obj.codigo}: registro exportado')
    buffer.seek(0)
    return FileResponse(buffer,as_attachment=True,filename=f'raizes-{tipo}-{pk}.zip')
