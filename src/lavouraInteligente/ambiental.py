"""Public INPE/DETER ingestion and conservative, versioned spatial screening.

No result from DETER alone is treated as EUDR certification or automatic approval.
"""
import hashlib
import json
import math
from datetime import date, timedelta
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.db import transaction
from django.utils import timezone
from pyproj import CRS, Transformer
from shapely.geometry import shape
from shapely.ops import transform

from .cloud import enqueue
from .models import AnaliseAmbiental, EventoAuditoria, Talhao

ENDPOINT='https://terrabrasilis.dpi.inpe.br/geoserver/ows'
LAYERS={'AMAZONIA':'deter-amz:deter_amz','CERRADO':'deter-cerrado-nb:deter_cerrado'}
CUTOFF=date(2020,12,31)
MAX_FEATURES=2000
MAX_BYTES=20*1024*1024

def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()

def geometry(value):
    geom=shape(value)
    if geom.geom_type not in ('Polygon','MultiPolygon') or geom.is_empty or not geom.is_valid or geom.area<=0:
        raise ValueError('Polígono vazio ou topologicamente inválido.')
    a,b,c,d=geom.bounds
    if not (-74<=a<=c<=-34 and -34<=b<=d<=6):raise ValueError('Geometria fora da área de consulta.')
    return geom

def fetch_layer(layer,bounds):
    # WFS 1.0 with explicit XY EPSG:4326 avoids the WFS 2 latitude/longitude ambiguity.
    params={'service':'WFS','version':'1.0.0','request':'GetFeature','typeName':layer,
        'outputFormat':'application/json','srsName':'EPSG:4326',
        'bbox':','.join(str(round(v,7)) for v in bounds)+',EPSG:4326','maxFeatures':MAX_FEATURES}
    url=ENDPOINT+'?'+urlencode(params)
    with urlopen(Request(url,headers={'User-Agent':'Raizes-Academic/1.0'}),timeout=20) as response:
        raw=response.read(MAX_BYTES+1)
    if len(raw)>MAX_BYTES:raise ValueError('Fonte ultrapassou o limite de tamanho.')
    result=json.loads(raw)
    if result.get('type')!='FeatureCollection' or not isinstance(result.get('features'),list):
        raise ValueError('Resposta inválida do serviço ambiental.')
    total=result.get('totalFeatures',result.get('numberMatched'))
    if len(result['features'])>=MAX_FEATURES or (isinstance(total,int) and total>len(result['features'])):
        raise ValueError('Consulta truncada. Reduza a área do talhão.')
    return result,hashlib.sha256(raw).hexdigest(),url

def evaluate(polygon,datasets,buffer_m=100):
    geom=geometry(polygon)
    point=geom.centroid
    crs=CRS.from_proj4(f'+proj=aeqd +lat_0={point.y} +lon_0={point.x} +datum=WGS84 +units=m')
    project=Transformer.from_crs('EPSG:4326',crs,always_xy=True).transform
    area=transform(project,geom)
    evidence=[];invalid=0
    for source,data in datasets.items():
        for feature in data['features']:
            try:
                props=feature['properties'];day=date.fromisoformat(str(props.get('view_date',''))[:10])
                if day<=CUTOFF:continue
                other=geometry(feature['geometry'])
                other=transform(project,other)
                distance=area.distance(other)
                if distance>buffer_m:continue
                overlap=area.intersection(other).area
                category=str(props.get('classname','')).upper()
                evidence.append({'id':feature.get('id',str(props.get('gid',''))),'fonte':source,
                    'data_deteccao':str(day),'classe':category,'distancia_m':round(distance,2),
                    'area_intersecao_m2':round(overlap,2),
                    'geometria':feature['geometry'],
                    'bloqueante':overlap>0 and category.startswith('DESMATAMENTO')})
            except (ValueError,KeyError,TypeError):invalid+=1
    blocked=any(e['bloqueante'] for e in evidence)
    status='BLOQUEADO' if blocked else 'REVISAO'
    reason=('Interseção com alerta DETER de desmatamento posterior a 31/12/2020.' if blocked else
        'Alerta próximo ou de degradação exige revisão.' if evidence else
        'Sem alerta DETER na consulta. MapBiomas/Sentinel e cobertura das fontes ainda pendentes.')
    if invalid:reason+=f' {invalid} feição(ões) inválida(s) na fonte; análise incompleta.'
    return {'status':status,'motivo':reason,'alertas':evidence,'feicoes_invalidas':invalid,
        'buffer_m':buffer_m,'corte':str(CUTOFF),'cobertura_completa':False,
        'limitacoes':['DETER é alerta de monitoramento; não comprova isoladamente conformidade EUDR.',
          'Datas de detecção não provam a data exata da supressão.',
          'Consulta pública pode ter defasagem. MapBiomas e Sentinel não integrados nesta análise.']}

def analyze(pk,actor=None):
    before=Talhao.objects.get(pk=pk)
    polygon=before.poligono
    sha=hashlib.sha256(canonical(polygon)).hexdigest()
    now=timezone.now();datasets={};sources=[];errors=[]
    try:
        geom=geometry(polygon)
        # A small outward envelope includes the configured 100m proximity zone everywhere in Brazil.
        a,b,c,d=geom.bounds
        pad=.002
        if (c-a)*(d-b)>1:raise ValueError('Área de consulta excessiva; divida em talhões menores.')
        for name,layer in LAYERS.items():
            try:
                data,digest,url=fetch_layer(layer,(a-pad,b-pad,c+pad,d+pad))
                datasets[name]=data;sources.append({'fonte':'INPE/DETER '+name,'camada':layer,
                    'url':url,'sha256':digest,'feicoes':len(data['features']),'consultado_em':now.isoformat()})
            except Exception as exc:errors.append(name+': '+type(exc).__name__)
        result=evaluate(polygon,datasets)
    except (ValueError,TypeError,KeyError) as exc:
        result={'status':'REVISAO','motivo':str(exc),'alertas':[],'cobertura_completa':False}
    if errors:
        result['falhas_fontes']=errors
        result['motivo']+=' Fonte indisponível ou resposta incompleta: '+', '.join(errors)+'.'
    result['fontes']=sources
    with transaction.atomic():
        plot=Talhao.objects.select_for_update().get(pk=pk)
        if hashlib.sha256(canonical(plot.poligono)).hexdigest()!=sha:
            raise ValueError('O polígono mudou durante a consulta; execute a análise novamente.')
        previous=plot.status
        # An incomplete later query cannot erase an existing environmental block.
        if previous=='BLOQUEADO' and result['status']!='BLOQUEADO':
            result['status']='BLOQUEADO';result['motivo']+=' Bloqueio anterior preservado até revisão humana.'
        analysis=AnaliseAmbiental.objects.create(talhao=plot,autor=actor,poligono_sha256=sha,
            poligono=polygon,status=result['status'],resultado=result,datasets=datasets,
            valido_ate=now+timedelta(hours=24))
        plot.status=result['status'];attrs=dict(plot.atributos)
        attrs['analise_ambiental']={'id':analysis.id,'motivo':result['motivo'],
            'calculado_em':now.isoformat(),'valido_ate':analysis.valido_ate.isoformat(),'poligono_sha256':sha}
        plot.atributos=attrs;plot.save(update_fields=['status','atributos','atualizado_em'])
        EventoAuditoria.objects.create(ator=actor,acao='ANALISE_AMBIENTAL',recurso='talhao',recurso_id=pk,
            descricao=f'{plot.codigo}: análise ambiental INPE/DETER',dados={'analise':analysis.id,'de':previous,'para':plot.status,'motivo':result['motivo']})
        payload={'analise':analysis.id,'talhao':pk,'codigo':plot.codigo,'poligono_sha256':sha,
            'status':plot.status,'calculado_em':now.isoformat(),'valido_ate':analysis.valido_ate.isoformat(),'resultado':result}
        enqueue('EVIDENCIA',f'ambiental/talhao-{pk}/analise-{analysis.id}.json',{**payload,'poligono':polygon,'datasets':datasets})
        summary={k:v for k,v in payload.items() if k!='resultado'}
        summary.update(motivo=result['motivo'],alertas=len(result['alertas']),cobertura_completa=False)
        enqueue('STATUS',f'TALHAO#{pk}',summary)
        if previous!=plot.status:enqueue('ALERTA',f'ANALISE#{analysis.id}',summary)
    return analysis
