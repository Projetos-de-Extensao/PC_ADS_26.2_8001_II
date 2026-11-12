"""Academic scenarios: synthetic providers and virtual flight/upload metadata.

No satellite/drone imagery is fabricated as a real observation. No 5GB payload is sent.
"""
import hashlib
import uuid
from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from pyproj import Geod,CRS,Transformer
from shapely.geometry import mapping
from shapely.ops import transform

from .ambiental import canonical,evaluate,geometry
from .cloud import enqueue
from .models import (AnaliseAmbiental,CenarioSimulado,EventoAuditoria,Fazenda,Produtor,
                     Talhao,UploadSimulado,Vistoria)

CENARIOS={
    'livre':('Área sem alertas','Três fontes sintéticas disponíveis e sem ocorrência.'),
    'proximidade':('Alerta próximo','Alerta a menos de 100 metros, sem interseção.'),
    'desmatamento':('Interseção com desmatamento','Ocorrência sintética posterior à data de corte.'),
    'nuvens':('Imagem com nuvens','A observação óptica sintética não permite concluir a análise.'),
    'fonte_indisponivel':('Fonte indisponível','Demonstra a falha de uma integração sem aprovar a origem.'),
    'vencido':('Análise vencida','O prazo de consulta expirou e exige nova análise.'),
}
PERFIS_VOO={'valido':.98,'cobertura_insuficiente':.60,'antigo':.98,'sem_georreferencia':None}

def quadrado(x,y,w=.002):
    return {'type':'Polygon','coordinates':[[[x,y],[x+w,y],[x+w,y+w],[x,y+w],[x,y]]]}

def evento(actor,action,plot,text,data):
    return EventoAuditoria.objects.create(ator=actor,acao=action,recurso='talhao',recurso_id=plot.pk,
        descricao=f'{plot.codigo}: {text}',dados={'simulado':True,**data})

@transaction.atomic
def criar(cenario,actor,key=None):
    if cenario not in CENARIOS:raise ValueError('Escolha um cenário disponível.')
    key=uuid.UUID(str(key)) if key else uuid.uuid4()
    previous=CenarioSimulado.objects.filter(idempotencia=key).first()
    if previous:return previous
    if CenarioSimulado.objects.count()>=200:raise ValueError('O laboratório atingiu 200 cenários preservados.')
    producer,_=Produtor.objects.get_or_create(documento='DEMO-RAIZES',defaults={
        'nome':'Cooperado fictício · laboratório','municipio':'Cristalina','uf':'GO'})
    producer=Produtor.objects.select_for_update().get(pk=producer.pk)
    farm,_=Fazenda.objects.get_or_create(produtor=producer,nome='Fazenda virtual Raízes',defaults={
        'municipio':'Cristalina','uf':'GO','area_ha':1000,'car_codigo':'DEMONSTRACAO-SEM-CAR-REAL'})
    previous=CenarioSimulado.objects.filter(idempotencia=key).first()
    if previous:return previous
    ident=uuid.uuid4();offset=(ident.int%20)*.004
    polygon=quadrado(-47.60+offset,-16.80)
    geod=Geod(ellps='WGS84');area=abs(geod.geometry_area_perimeter(geometry(polygon))[0])/10000
    plot=Talhao.objects.create(fazenda=farm,codigo='DEMO-'+ident.hex[:10].upper(),cultura='soja',
        area_ha=round(area,2),poligono=polygon,status='REVISAO',atributos={'ambiente':'SIMULACAO'})
    run=CenarioSimulado.objects.create(id=ident,idempotencia=key,talhao=plot,cenario=cenario,autor=actor)
    now=timezone.now();sha=hashlib.sha256(canonical(polygon)).hexdigest()
    datasets={name:{'type':'FeatureCollection','features':[],'simulado':True}
        for name in ['DETER_SIMULADO','MAPBIOMAS_SIMULADO']}
    x,y=polygon['coordinates'][0][0]
    if cenario in ('proximidade','desmatamento'):
        alert=quadrado(x+.0024,y) if cenario=='proximidade' else quadrado(x+.0005,y+.0005,.001)
        datasets['MAPBIOMAS_SIMULADO']['features']=[{'type':'Feature','id':'SIM-'+ident.hex[:12],
            'geometry':alert,'properties':{'classname':'DESMATAMENTO_CR','view_date':timezone.localdate(now).isoformat(),'simulado':True}}]
    result=evaluate(polygon,datasets)
    result['motivo']='Simulação: '+result['motivo']
    if cenario=='desmatamento':result['motivo']='Simulação: interseção com alerta sintético de desmatamento posterior à data de corte.'
    complete=cenario not in ('fonte_indisponivel','nuvens')
    if cenario=='livre':result.update(status='APROVADO',motivo='Simulação: fontes sintéticas completas, sem interseção ou proximidade.')
    if cenario=='nuvens':result.update(status='REVISAO',motivo='Simulação: 85% de nuvens impedem concluir a observação óptica.')
    if cenario=='fonte_indisponivel':result.update(status='REVISAO',motivo='Simulação: provedor MapBiomas indisponível; análise incompleta.')
    if cenario=='vencido':result.update(status='REVISAO',motivo='Simulação: análise vencida; a balança exige nova avaliação.')
    result.update(simulado=True,cenario=cenario,cobertura_completa=complete,
        limitacoes=['Dados inteiramente sintéticos para apresentação acadêmica; não são observações das plataformas citadas.'],
        fontes=[{'fonte':name,'simulado':True,'situacao':'INDISPONIVEL' if cenario=='fonte_indisponivel' and name=='MapBiomas' else 'DISPONIVEL'}
            for name in ['DETER','MapBiomas','Sentinel']],
        sentinel={'simulado':True,'nuvens_percentual':85 if cenario=='nuvens' else 5,
            'bandas':{'NIR':.8,'VERMELHO':.1},'ndvi':None if cenario=='nuvens' else round((.8-.1)/(.8+.1),4)})
    expires=now+timedelta(hours=-1 if cenario=='vencido' else 24)
    analysis=AnaliseAmbiental.objects.create(talhao=plot,autor=actor,poligono_sha256=sha,poligono=polygon,
        status=result['status'],resultado=result,datasets=datasets,valido_ate=expires)
    plot.status=result['status'];plot.atributos.update({'simulacao':str(run.pk),
        'analise_ambiental':{'id':analysis.pk,'motivo':result['motivo'],'simulado':True,
            'calculado_em':now.isoformat(),'valido_ate':expires.isoformat(),'poligono_sha256':sha}})
    plot.save(update_fields=['status','atributos','atualizado_em'])
    run.dados={'analise':analysis.pk,'resultado':result};run.save(update_fields=['dados'])
    evento(actor,'SIMULAR_ANALISE',plot,'cenário acadêmico executado',{'cenario':cenario,'analise':analysis.pk})
    enqueue('EVIDENCIA',f'demonstracao/{run.pk}/analise.json',{'simulado':True,'poligono':polygon,
        'resultado':result,'datasets':datasets,'poligono_sha256':sha})
    enqueue('ALERTA',f'DEMO#{run.pk}',{'simulado':True,'cenario':cenario,'talhao':plot.pk,'status':plot.status})
    return run

@transaction.atomic
def iniciar_voo(run,profile,actor):
    if profile not in PERFIS_VOO:raise ValueError('Perfil de voo inválido.')
    plot=Talhao.objects.select_for_update().get(pk=run.talhao_id)
    if plot.status!='REVISAO':raise ValueError('Somente um talhão em revisão pode receber voo de vistoria.')
    if run.uploads.filter(status='EM_ENVIO').exists():raise ValueError('Conclua ou cancele o envio que já está aberto.')
    now=timezone.localdate()
    inspection=Vistoria.objects.filter(talhao=plot,status__in=['SOLICITADA','AGENDADA']).first()
    if not inspection:inspection=Vistoria.objects.create(talhao=plot,solicitante=actor,
        motivo='DEMONSTRAÇÃO: vistoria virtual do cenário '+run.cenario,prazo=now)
    inspection.status='AGENDADA';inspection.save(update_fields=['status'])
    a,b,c,d=geometry(plot.poligono).bounds
    ratio=PERFIS_VOO[profile]
    coverage=None if ratio is None else {'type':'Polygon','coordinates':[[[a,b],[a+(c-a)*ratio,b],
        [a+(c-a)*ratio,d],[a,d],[a,b]]]}
    row=UploadSimulado.objects.create(cenario=run,vistoria=inspection,autor=actor,perfil_voo=profile,
        poligono_sha256=hashlib.sha256(canonical(plot.poligono)).hexdigest(),cobertura=coverage,
        data_voo=now-timedelta(days=10 if profile=='antigo' else 0))
    evento(actor,'INICIAR_VOO_SIMULADO',plot,'envio virtual iniciado',{'upload':str(row.pk),'bytes_reais_transferidos':0})
    return row

@transaction.atomic
def enviar_parte(pk,number):
    row=UploadSimulado.objects.select_for_update().get(pk=pk)
    if row.status!='EM_ENVIO':raise ValueError('Este envio não está aberto.')
    if isinstance(number,bool) or not isinstance(number,int) or not 1<=number<=row.total_partes:
        raise ValueError('Número de parte inválido.')
    key=str(number)
    row.partes.setdefault(key,hashlib.sha256(canonical({'upload':str(row.pk),'parte':number,'simulado':True})).hexdigest())
    row.save(update_fields=['partes'])
    return row

@transaction.atomic
def concluir_voo(pk,actor):
    row=UploadSimulado.objects.select_for_update().select_related('cenario__talhao','vistoria').get(pk=pk)
    if row.status!='EM_ENVIO':return row
    if set(row.partes)!={str(n) for n in range(1,row.total_partes+1)}:
        raise ValueError('Envie todas as partes antes de validar o voo.')
    plot=Talhao.objects.select_for_update().get(pk=row.cenario.talhao_id)
    if hashlib.sha256(canonical(plot.poligono)).hexdigest()!=row.poligono_sha256:
        raise ValueError('O polígono mudou durante o envio. Inicie uma nova vistoria.')
    errors=[];coverage=0
    if row.cobertura:
        geom=geometry(plot.poligono);point=geom.centroid
        crs=CRS.from_proj4(f'+proj=aeqd +lat_0={point.y} +lon_0={point.x} +datum=WGS84 +units=m')
        project=Transformer.from_crs('EPSG:4326',crs,always_xy=True).transform
        area=transform(project,geom);footprint=transform(project,geometry(row.cobertura))
        coverage=100*area.intersection(footprint).area/area.area
        if coverage<95:errors.append('Cobertura inferior a 95% do talhão.')
    else:errors.append('Georreferência ausente.')
    last=plot.analises.first()
    if row.data_voo>timezone.localdate() or (last and row.data_voo<timezone.localdate(last.criado_em)):
        errors.append('Data do voo inválida ou anterior à análise que motivou a vistoria.')
    manifest={'simulado':True,'upload':str(row.pk),'partes':row.partes,'tamanho_declarado':row.tamanho_declarado,
        'bytes_reais_transferidos':0,'poligono':plot.poligono,'poligono_sha256':row.poligono_sha256,'cobertura':row.cobertura,'data_voo':str(row.data_voo)}
    row.validacao={'simulado':True,'apto_para_revisao':not errors,'cobertura_percentual':round(coverage,2),
        'erros':errors,'manifesto':manifest,'sha256':hashlib.sha256(canonical(manifest)).hexdigest()}
    row.status='REJEITADO' if errors else 'VALIDADO';row.save(update_fields=['status','validacao'])
    if not errors:row.vistoria.status='RECEBIDA';row.vistoria.save(update_fields=['status'])
    evento(actor,'VALIDAR_VOO_SIMULADO',plot,'voo virtual '+row.status.lower(),{'upload':str(row.pk),**row.validacao})
    enqueue('EVIDENCIA',f'demonstracao/{row.cenario_id}/voo-{row.pk}.json',row.validacao)
    return row
