import json
import statistics
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import os
BASE = os.environ.get('AP2_BASE_URL', 'http://127.0.0.1:8000').rstrip('/')
stamp = datetime.now(timezone.utc).strftime('%m%d%H%M%S')
report = []
created = []

def request(method, path, data=None, expected=200):
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(BASE + path, data=body, method=method,
                                 headers={'Content-Type': 'application/json'})
    try:
        response = urllib.request.urlopen(req, timeout=20)
    except urllib.error.HTTPError as error:
        response = error
    raw = response.read().decode()
    result = json.loads(raw) if raw else None
    assert response.status == expected, (method, path, response.status, result)
    report.append(f'{method} {path} -> {response.status}')
    return result

def create(resource, data):
    result = request('POST', f'/api/{resource}/', data, 201)
    created.append(f'/api/{resource}/{result["id"]}/')
    return result

try:
    request('GET', '/api/')
    produtor = create('produtores', {'nome':'Verificacao AP2', 'documento':'AP2'+stamp,
                                   'municipio':'Cristalina', 'uf':'GO'})
    fazenda = create('fazendas', {'produtor':produtor['id'], 'nome':'Fazenda AP2',
                     'car_codigo':'AP2-'+stamp, 'municipio':'Cristalina', 'uf':'GO','area_ha':'10.00'})
    talhao = create('talhoes', {'fazenda':fazenda['id'], 'codigo':'AP2-T-'+stamp,
                     'cultura':'soja','area_ha':'2.00','status':'APROVADO',
                     'poligono':{'type':'Polygon','coordinates':[[[-47,-16],[-47.01,-16],[-47.01,-16.01],[-47,-16]]]},
                     'atributos':{'bioma':'cerrado','evidencia':'v'+stamp,'ndvi':0.8}})
    lote = create('lotes', {'codigo':'AP2-L-'+stamp,'peso_total_kg':'100.00'})
    item = create('lote-itens', {'lote':lote['id'],'talhao':talhao['id'],'peso_kg':'100.00'})
    objects = [('produtores',produtor,{'nome':'Verificacao AP2 atualizada'}),
               ('fazendas',fazenda,{'nome':'Fazenda AP2 atualizada'}),
               ('talhoes',talhao,{'cultura':'milho'}),
               ('lotes',lote,{'motivo':'Validacao CRUD'}),
               ('lote-itens',item,{'peso_kg':'99.00'})]
    for resource, obj, patch in objects:
        path=f'/api/{resource}/{obj["id"]}/'
        current=request('GET',path)
        request('PUT',path,current)
        changed=request('PATCH',path,patch)
        for key,value in patch.items():
            assert changed[key] == value
        request('GET',f'/api/{resource}/')
    nested=request('GET',f'/api/produtores/{produtor["id"]}/')
    assert nested['fazendas'][0]['talhoes'][0]['id']==talhao['id']
    filtered=request('GET','/api/talhoes/?'+urllib.parse.urlencode({'atributos__evidencia':'v'+stamp}))
    assert [x['id'] for x in filtered]==[talhao['id']]
    before_lotes=len(request('GET','/api/lotes/'))
    before_itens=len(request('GET','/api/lote-itens/'))
    for suffix,total,itens in [('PESO','999.00',[{'talhao':talhao['id'],'peso_kg':'100.00'}]),
                              ('REPETIDO','200.00',[{'talhao':talhao['id'],'peso_kg':'100.00'}]*2)]:
        request('POST','/api/lotes/receber/',{'codigo':'AP2-'+suffix+'-'+stamp,
                'peso_total_kg':total,'itens':itens},409)
        assert len(request('GET','/api/lotes/'))==before_lotes
        assert len(request('GET','/api/lote-itens/'))==before_itens
    recebido=request('POST','/api/lotes/receber/',{'codigo':'AP2-RECEBER-'+stamp,
                    'peso_total_kg':'100.00','itens':[{'talhao':talhao['id'],'peso_kg':'100.00'}]},201)
    assert recebido['status']=='APROVADO' and len(recebido['itens'])==1
    created.append(f'/api/lotes/{recebido["id"]}/')
    for child in recebido['itens']:
        created.append(f'/api/lote-itens/{child["id"]}/')
    elapsed=[]
    for _ in range(20):
        start=time.perf_counter()
        request('GET','/api/talhoes/')
        elapsed.append((time.perf_counter()-start)*1000)
    report.append(f'20 GET sequenciais externos: p50={statistics.median(elapsed):.1f} ms; '
                  f'p95={sorted(elapsed)[18]:.1f} ms. Dataset de demonstracao, sem teste de carga.')
finally:
    for path in reversed(created):
        try:
            request('DELETE',path,expected=204)
        except Exception as exc:
            report.append(f'ERRO DE LIMPEZA {path}: {exc}')
    output=Path.cwd()/'public-api-validation.log'
    output.write_text('\n'.join(report)+'\n',encoding='utf-8')
    print('\n'.join(report))

