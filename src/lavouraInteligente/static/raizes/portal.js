/* Raízes — interface operacional, com dados persistidos no Django. */
'use strict';
const $ = (q, root = document) => root.querySelector(q);
const $$ = (q, root = document) => [...root.querySelectorAll(q)];
const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const icon = name => `<svg aria-hidden="true"><use href="#i-${name}"/></svg>`;
const number = (value, digits = 0) => new Intl.NumberFormat('pt-BR', {maximumFractionDigits:digits}).format(Number(value) || 0);
const when = value => value ? new Intl.DateTimeFormat('pt-BR',{day:'2-digit',month:'short',year:'numeric',hour:'2-digit',minute:'2-digit'}).format(new Date(value)) : '—';
const dateOnly = value => value ? new Intl.DateTimeFormat('pt-BR',{day:'2-digit',month:'short',year:'numeric'}).format(new Date(value+'T12:00:00')) : '—';
const labelStatus = {APROVADO:'Aprovado',REVISAO:'Em revisão',BLOQUEADO:'Bloqueado',SOLICITADA:'Solicitada',AGENDADA:'Agendada',RECEBIDA:'Recebida'};
const statusClass = status => status==='REVISAO' || status==='SOLICITADA' ? 'review' : status==='BLOQUEADO' ? 'blocked' : ['AGENDADA','RECEBIDA'].includes(status) ? 'neutral' : '';
const badge = status => `<span class="status ${statusClass(status)}">${esc(labelStatus[status] || status)}</span>`;
const names = {inicio:'Visão geral',talhoes:'Talhões e mapa',lotes:'Recepção de lotes',produtores:'Produtores',fazendas:'Fazendas',vistorias:'Vistorias',historico:'Histórico e evidências',integracoes:'Monitoramento ambiental',laboratorio:'Laboratório',relatorios:'Relatórios',guia:'Como funciona'};
let state = null, brazil = null, route = 'inicio', mapBounds = null;
let filters = {q:'',status:'',municipio:'',produtor:'',de:'',ate:''};
let receiptItems = [], selectedTalhao = null;
let preserveFiltersOnHash = false;
let integrationState=null;
const farm = id => state.fazendas.find(x => x.id===Number(id));
const producer = id => state.produtores.find(x => x.id===Number(id));
const plot = id => state.talhoes.find(x => x.id===Number(id));
const lot = id => state.lotes.find(x => x.id===Number(id));
const initials = name => String(name).trim().split(/\s+/).map(x=>x[0]).slice(0,2).join('').toUpperCase();

async function api(url, method='GET', data) {
  const csrf = document.cookie.split('; ').find(x=>x.startsWith('csrftoken='))?.split('=')[1] || '';
  const options = {method,credentials:'same-origin',headers:{Accept:'application/json','X-CSRFToken':decodeURIComponent(csrf)}};
  if (data instanceof FormData) options.body=data;
  else if (data !== undefined) {options.headers['Content-Type']='application/json';options.body=JSON.stringify(data);}
  const response=await fetch(url,options);
  const content=response.headers.get('content-type') || '';
  if (!content.includes('application/json') && response.status!==204) {
    if (response.url.includes('/entrar/')) {location.assign('/entrar/?next=/');throw new Error('Sua sessão terminou. Entre novamente.');}
    throw new Error('Não foi possível concluir a operação. Tente novamente.');
  }
  const result=response.status===204 ? null : await response.json();
  if (!response.ok) {
    const message=result?.detalhe || result?.detail || Object.entries(result || {}).map(([key,value])=>`${key}: ${Array.isArray(value)?value.join(' '):value}`).join(' · ');
    throw new Error(message || `Não foi possível concluir a operação (${response.status}).`);
  }
  return result;
}

function toast(message,error=false) {
  const el=document.createElement('div');el.className='toast'+(error?' error':'');el.textContent=message;
  $('#toasts').append(el);setTimeout(()=>el.remove(),6500);
}

async function refresh(renderPage=true) {
  state=await api('/app/estado/');
  $('#profile-name').textContent=state.usuario.nome;
  $('#profile-role').textContent=state.usuario.perfil;
  $('#profile-initials').textContent=initials(state.usuario.nome);
  $('#nav-talhao-count').textContent=state.talhoes.length;
  $('#connection-label').textContent='Dados da cooperativa';
  $('#notification-dot').hidden=!state.historico.length;
  integrationState=await api('/app/integracoes/');
  [laboratorioState,reportState]=await Promise.all([api('/app/laboratorio/'),api('/app/relatorios/')]);
  if (renderPage) render();
}

const actionButton = (text,action,id='',kind='') => `<button class="button ${kind}" data-action="${action}" data-id="${id}">${esc(text)}</button>`;
function heading(eyebrow,title,description,button='') {
  const today=new Intl.DateTimeFormat('pt-BR',{day:'numeric',month:'long',year:'numeric'}).format(new Date());
  return `<section class="page-head"><div><span class="eyebrow">${esc(eyebrow)}</span><h1>${esc(title)}</h1><p>${esc(description)}</p></div><div class="head-actions"><span class="date-label">${esc(today)}</span>${button}</div></section>`;
}
function empty(title,description) {return `<div class="empty"><strong>${esc(title)}</strong>${esc(description)}</div>`;}
function metric(title,value,unit,note,ico,warning=false) {
  return `<article class="kpi-card ${warning?'warning':''}"><div class="kpi-top">${esc(title)}<span class="kpi-icon">${icon(ico)}</span></div><div class="kpi-value">${esc(value)}${unit?`<small>${esc(unit)}</small>`:''}</div><div class="kpi-note"><i class="tiny-dot"></i>${esc(note)}</div></article>`;
}
function table(headers,rows,footer) {
  return `<div class="panel"><div class="table-wrap"><table class="data-table"><thead><tr>${headers.map(x=>`<th>${esc(x)}</th>`).join('')}</tr></thead><tbody>${rows.join('') || `<tr><td colspan="${headers.length}">${empty('Nenhum registro encontrado','Ajuste os filtros ou cadastre um novo registro.')}</td></tr>`}</tbody></table></div><div class="table-footer"><span>${esc(footer)}</span><span>Dados persistidos na cooperativa</span></div></div>`;
}
function filteredPlots() {
  const q=filters.q.toLocaleLowerCase('pt-BR');
  return state.talhoes.filter(t=>{
    const f=farm(t.fazenda),p=producer(f?.produtor);
    return (!filters.status || t.status===filters.status) && (!filters.produtor || String(p?.id)===filters.produtor) &&
      (!filters.municipio || f?.municipio===filters.municipio) &&
      (!q || [t.codigo,t.cultura,f?.nome,f?.municipio,p?.nome].join(' ').toLocaleLowerCase('pt-BR').includes(q));
  });
}
function plotRows(plots) {
  return plots.map(t=>{const f=farm(t.fazenda),p=producer(f?.produtor);
    return `<tr data-talhao="${t.id}"><td><strong>${esc(t.codigo)}${t.atributos?.ambiente==='SIMULACAO'?'<em class="sim-label">SIMULAÇÃO</em>':''}</strong><small>${esc(t.cultura)}</small></td><td>${esc(f?.nome || '—')}<small>${esc(f?.municipio || '')} · ${esc(f?.uf || '')}</small></td><td>${esc(p?.nome || '—')}</td><td>${number(t.area_ha,2)} ha</td><td>${badge(t.status)}</td><td><button class="row-action" data-action="detail" data-id="${t.id}" aria-label="Ver ${esc(t.codigo)}">↗</button></td></tr>`;
  });
}

function rings(geometry) {
  if (!geometry || !Array.isArray(geometry.coordinates))return [];
  if (geometry.type==='Polygon')return geometry.coordinates;
  if (geometry.type==='MultiPolygon')return geometry.coordinates.flat();
  return [];
}
function plotBounds(plots,padding=.15) {
  const pts=plots.flatMap(t=>rings(t.poligono).flat()).filter(p=>Array.isArray(p)&&Number.isFinite(p[0])&&Number.isFinite(p[1]));
  if(!pts.length)return [-74,-34,-34,6];
  let xs=pts.map(p=>p[0]),ys=pts.map(p=>p[1]);
  const a=Math.min(...xs),b=Math.max(...xs),c=Math.min(...ys),d=Math.max(...ys),px=Math.max((b-a)*padding,.004),py=Math.max((d-c)*padding,.004);
  return [a-px,c-py,b+px,d+py];
}
function mapSVG(plots,bounds=null,big=false,detail=false) {
  const mobile=window.innerWidth<=720;
  const width=mobile?360:760,height=detail?310:big?430:mobile?300:330;
  const b=bounds || [-74,-34,-34,6];
  const scale=Math.min((width-60)/(b[2]-b[0]),(height-42)/(b[3]-b[1]));
  const cx=(b[0]+b[2])/2,cy=(b[1]+b[3])/2;
  const xy=p=>[(p[0]-cx)*scale+width/2,(cy-p[1])*scale+height/2];
  const path=ring=>ring.map((p,i)=>`${i?'L':'M'}${xy(p)[0].toFixed(2)},${xy(p)[1].toFixed(2)}`).join(' ')+' Z';
  let lines='';
  for(let i=1;i<12;i++) lines+=`<line class="gridline" x1="${i*width/12}" y1="0" x2="${i*width/12}" y2="${height}"/>`;
  for(let i=1;i<7;i++) lines+=`<line class="gridline" x1="0" y1="${i*height/7}" x2="${width}" y2="${i*height/7}"/>`;
  const country=brazil?rings(brazil).map(r=>`<path class="country" d="${path(r)}"/>`).join(''):'';
  let environmental='';
  if(scale>45 && integrationState) for(const t of plots){
    const last=integrationState.analises.find(a=>a.talhao===t.id);
    for(const alert of last?.resultado.alertas || []){
      environmental+=rings(alert.geometria).map(r=>`<path d="${path(r)}" fill="#a65b41" fill-opacity=".18" stroke="#a65b41" stroke-dasharray="4 3" stroke-width="1.5"><title>${esc(alert.fonte)} · ${esc(alert.classe)} · ${esc(alert.data_deteccao)}</title></path>`).join('');
    }
  }
  const colors={APROVADO:'#66945d',REVISAO:'#c5a04b',BLOQUEADO:'#bb7863'};
  const groups=[];let shapes='';
  for(const t of plots) {
    const rs=rings(t.poligono);if(!rs.length || !rs[0].length)continue;
    const points=rs[0],center=[points.reduce((s,p)=>s+p[0],0)/points.length,points.reduce((s,p)=>s+p[1],0)/points.length],pos=xy(center);
    if (scale>45) shapes+=rs.map(r=>`<path d="${path(r)}" fill="${colors[t.status]}" fill-opacity=".25" stroke="${colors[t.status]}" stroke-width="2"/>`).join('');
    if(pos[0]<0 || pos[0]>width || pos[1]<0 || pos[1]>height)continue;
    const group=groups.find(g=>Math.hypot(g.x-pos[0],g.y-pos[1])<22);
    if(group)group.items.push(t);else groups.push({x:pos[0],y:pos[1],items:[t]});
  }
  const markers=groups.map(g=>{
    const worst=g.items.some(t=>t.status==='BLOQUEADO')?'BLOQUEADO':g.items.some(t=>t.status==='REVISAO')?'REVISAO':'APROVADO';
    const isGroup=g.items.length>1,ids=g.items.map(t=>t.id).join(','),name=isGroup?`${g.items.length} talhões`:g.items[0].codigo;
    const action=isGroup?'map-cluster':'detail';
    return `<g class="marker" tabindex="0" role="button" aria-label="${esc(name)}" data-action="${action}" data-id="${ids}" transform="translate(${g.x},${g.y})"><title>${esc(name)}</title><circle r="${isGroup?14:9}" fill="${colors[worst]}" opacity=".13"/><circle r="${isGroup?10:5}" fill="${colors[worst]}" stroke="white" stroke-width="2"/>${isGroup?`<text text-anchor="middle" y="3" fill="white" font-size="9" font-family="Segoe UI">${g.items.length}</text>`:''}${scale<45?`<text x="${isGroup?18:13}" y="4" class="map-label" style="font-size:7px;letter-spacing:.2px">${esc(farm(g.items[0].fazenda)?.municipio || '')}</text>`:''}</g>`;
  }).join('');
  return `<svg class="map-svg ${big?'big':''}" viewBox="0 0 ${width} ${height}" role="img" aria-label="Mapa dos polígonos e origens cadastradas"><rect width="${width}" height="${height}" fill="#f0f2e9"/>${lines}${country}${environmental}${shapes}${!bounds?`<text x="${width/2-10}" y="${height*.58}" class="map-label" opacity=".6">B R A S I L</text>`:''}${markers}<text x="16" y="${height-13}" class="map-label" style="font-size:6px;letter-spacing:.5px">${detail?'POLÍGONO CADASTRADO · WGS84':'ORIGENS DA COOPERATIVA · WGS84'}</text></svg>`;
}
function mapPanel(plots,big=false) {
  const valid=plots.filter(t=>rings(t.poligono).length).length;
  return `<section class="panel map-panel"><div class="panel-head"><div><h2>Mapa de origens</h2><p>Os talhões cadastrados, por status operacional</p></div><div class="legend"><span><i></i>Aprovado</span><span><i class="review"></i>Em revisão</span><span><i class="blocked"></i>Bloqueado</span></div></div><div class="map-wrap"><div class="map-top-label">${mapBounds?'ÁREAS CADASTRADAS':'BRASIL · ORIGENS RASTREÁVEIS'}</div>${mapSVG(plots,mapBounds,big)}<div class="map-controls"><button data-action="map-zoom-in" aria-label="Ampliar mapa">+</button><button data-action="map-zoom-out" aria-label="Reduzir mapa">−</button><button data-action="map-fit" title="Ajustar aos talhões" aria-label="Ajustar aos talhões">⌖</button><button data-action="map-reset" title="Ver Brasil" aria-label="Ver Brasil">↺</button></div><div class="map-credit">Base: Natural Earth · polígonos do cadastro</div></div><div class="map-footer"><span>${valid} talhões com geometria · ${new Set(plots.map(t=>t.fazenda)).size} fazendas</span><a href="#talhoes">Explorar origens <span>↗</span></a></div></section>`;
}

function homePage() {
  const review=state.talhoes.filter(t=>t.status==='REVISAO').length;
  const attention=state.talhoes.filter(t=>t.status!=='APROVADO').sort((a,b)=>a.status==='BLOQUEADO'?-1:1);
  return heading('ACOMPANHAMENTO DA OPERAÇÃO','Uma visão clara de cada origem.','Acompanhe seus talhões, identifique riscos e decida com confiança.',`<button class="button primary" data-action="new-talhao">${icon('plus')}Novo talhão</button>`)+
   `<section class="kpi-grid">${metric('Talhões cadastrados',number(state.talhoes.length),'',`${state.fazendas.length} fazendas na operação`,'map')}${metric('Área acompanhada',number(state.talhoes.reduce((s,t)=>s+Number(t.area_ha),0),1),'ha','Área informada nos cadastros','leaf')}${metric('Aguardando revisão',number(review),'',review?'Precisam de análise da equipe':'Nenhuma revisão pendente','alert',true)}${metric('Lotes recebidos',number(state.lotes.length),'','Origens consultadas na balança','truck')}</section>`+
   `<div class="dashboard-grid">${mapPanel(state.talhoes)}<section class="panel priority-panel"><div class="panel-head"><div><h2>Prioridade de análise</h2><p>Origens que merecem atenção</p></div><span class="priority-tag">${attention.length}</span></div><div class="priority-list">${attention.slice(0,3).map(t=>`<article class="priority-item" data-talhao="${t.id}"><div class="priority-title"><strong>${esc(t.codigo)}</strong>${badge(t.status)}</div><p>${esc(farm(t.fazenda)?.nome)} · ${esc(t.cultura)}</p><p class="reason">${t.atributos.alertas?.length?`${t.atributos.alertas.length} alerta(s) informado(s) · fonte ${esc(t.atributos.fonte || 'não informada')}`:'Revisão de origem pendente pela equipe.'}</p><div class="priority-action">Analisar talhão ${icon('arrow')}</div></article>`).join('') || empty('Tudo em dia','Nenhum talhão exige revisão no momento.')}</div></section></div>`+
   `<div class="section-title"><div><h2>Talhões da cooperativa</h2><p>A situação de cada origem, em um só lugar</p></div><a href="#talhoes" class="button small">Ver todos ${icon('arrow')}</a></div>${table(['Talhão / cultura','Fazenda','Produtor','Área','Status',''],plotRows(state.talhoes.slice(0,6)),`${Math.min(state.talhoes.length,6)} de ${state.talhoes.length} talhões cadastrados`)}`;
}
function plotFilters() {
  const cities=[...new Set(state.fazendas.map(f=>f.municipio))].sort();
  return `<div class="filter-bar"><label class="filter-input">${icon('search')}<input data-filter="q" value="${esc(filters.q)}" placeholder="Buscar talhão, fazenda ou produtor" aria-label="Buscar talhões"></label><select data-filter="status" aria-label="Filtrar por status"><option value="">Todos os status</option>${Object.entries(labelStatus).slice(0,3).map(([k,v])=>`<option value="${k}" ${filters.status===k?'selected':''}>${v}</option>`).join('')}</select><select data-filter="produtor" aria-label="Filtrar por produtor"><option value="">Todos os produtores</option>${state.produtores.map(p=>`<option value="${p.id}" ${filters.produtor===String(p.id)?'selected':''}>${esc(p.nome)}</option>`).join('')}</select><select data-filter="municipio" aria-label="Filtrar por município"><option value="">Todos os municípios</option>${cities.map(c=>`<option ${filters.municipio===c?'selected':''}>${esc(c)}</option>`).join('')}</select><span class="filter-count">${filteredPlots().length} origens encontradas</span></div>`;
}
function plotsPage() {
  const list=filteredPlots();
  return heading('ORIGENS RASTREÁVEIS','Talhões e mapa','Encontre uma área e consulte seu cadastro, atributos e histórico.',`<button class="button primary" data-action="new-talhao">${icon('plus')}Novo talhão</button>`)+plotFilters()+mapPanel(list,true)+`<div class="section-title" style="margin-top:25px"><div><h2>Áreas cadastradas</h2></div></div>`+table(['Talhão / cultura','Fazenda','Produtor','Área','Status',''],plotRows(list),`${list.length} talhões nesta seleção`);
}
function lotsPage() {
  const list=state.lotes.filter(l=>(!filters.status || l.status===filters.status)&&(!filters.q || l.codigo.toLowerCase().includes(filters.q.toLowerCase()))&&(!filters.de || l.recebido_em.slice(0,10)>=filters.de)&&(!filters.ate || l.recebido_em.slice(0,10)<=filters.ate));
  const pending=state.lotes.filter(l=>!state.decisoes[l.id]).length;
  return heading('ORIGEM À VISTA, DECISÃO REGISTRADA','Recepção de lotes','Consulte as origens de cada carga antes de registrar o recebimento.',`<button class="button primary" data-action="receive">${icon('plus')}Receber lote</button>`)+
    `<section class="kpi-grid">${metric('Lotes registrados',number(state.lotes.length),'','Histórico da operação','truck')}${metric('Peso recebido',number(state.lotes.reduce((s,l)=>s+Number(l.peso_total_kg),0)/1000,2),'t','Soma dos pesos cadastrados','farm')}${metric('Decisão pendente',number(pending),'','Aguardando registro do operador','clock',true)}${metric('Origens bloqueadas',number(state.lotes.filter(l=>l.status==='BLOQUEADO').length),'lotes','Pior status entre os talhões','alert')}</section>`+
    `<div class="filter-bar"><label class="filter-input">${icon('search')}<input data-filter="q" value="${esc(filters.q)}" placeholder="Buscar código do lote" aria-label="Buscar lote"></label><select data-filter="status" aria-label="Filtrar status dos lotes"><option value="">Todos os status</option>${Object.entries(labelStatus).slice(0,3).map(([k,v])=>`<option value="${k}" ${filters.status===k?'selected':''}>${v}</option>`).join('')}</select><input type="date" data-filter="de" value="${esc(filters.de)}" aria-label="Data inicial"><input type="date" data-filter="ate" value="${esc(filters.ate)}" aria-label="Data final"><span class="filter-count">${list.length} lotes</span></div>`+
    table(['Lote','Recebimento','Peso','Origens','Status de origem','Decisão',''],list.map(l=>{const d=state.decisoes[l.id];return `<tr><td><strong>${esc(l.codigo)}</strong></td><td>${when(l.recebido_em)}</td><td>${number(l.peso_total_kg,2)} kg</td><td>${l.itens.length} talhão(ões)</td><td>${badge(l.status)}</td><td>${d?`<span class="status ${d.acao==='RECUSAR'?'blocked':''}">${d.acao==='ACEITAR'?'Aceito':'Recusado'}</span><small>${esc(d.operador)}</small>`:'<span class="muted" style="font-size:10px">Pendente</span>'}</td><td><button class="row-action" data-action="lot-detail" data-id="${l.id}" aria-label="Ver lote ${esc(l.codigo)}">↗</button></td></tr>`;}),`${list.length} lotes encontrados`);
}
function recordsPage(kind) {
  const isFarm=kind==='fazendas',list=state[kind].filter(x=>[x.nome,x.documento,x.car_codigo,x.municipio].join(' ').toLowerCase().includes(filters.q.toLowerCase()));
  return heading('CADASTROS DA COOPERATIVA',isFarm?'Fazendas':'Produtores',isFarm?'Organize as propriedades e conecte cada talhão à sua origem.':'Mantenha os responsáveis pelas origens e suas propriedades.',`<button class="button primary" data-action="new-record" data-kind="${kind}">${icon('plus')}${isFarm?'Nova fazenda':'Novo produtor'}</button>`)+
    `<div class="filter-bar"><label class="filter-input">${icon('search')}<input data-filter="q" value="${esc(filters.q)}" placeholder="Buscar nome, documento ou município" aria-label="Buscar cadastro"></label><span class="filter-count">${list.length} cadastros</span></div>`+
    table(isFarm?['Fazenda','Produtor','Município','Área','Talhões','Ações']:['Produtor','Documento','Município','Fazendas','Ações'],list.map(x=>isFarm?
      `<tr><td><strong>${esc(x.nome)}</strong><small>${esc(x.car_codigo || 'CAR não informado')}</small></td><td>${esc(producer(x.produtor)?.nome)}</td><td>${esc(x.municipio)} · ${esc(x.uf)}</td><td>${number(x.area_ha,2)} ha</td><td>${x.talhoes.length}</td><td>${recordActions(kind,x.id)}</td></tr>`:
      `<tr><td><strong>${esc(x.nome)}</strong></td><td>${esc(RaizesDocumento.mask(x.documento))}</td><td>${esc(x.municipio)} · ${esc(x.uf)}</td><td>${x.fazendas.length}</td><td>${recordActions(kind,x.id)}</td></tr>`),`${list.length} ${kind} nesta seleção`);
}
function recordActions(kind,id) {return `<button class="button small" data-action="edit-record" data-kind="${kind}" data-id="${id}">Editar</button> <button class="button text small" data-action="delete-record" data-kind="${kind}" data-id="${id}">Excluir</button>`;}
function inspectionsPage() {
  const list=state.vistorias.filter(v=>!filters.status || v.status===filters.status);
  return heading('ANÁLISE DE CAMPO','Vistorias por drone','Acompanhe as solicitações e reúna imagens para apoiar a análise.',actionButton('Solicitar vistoria','choose-inspection','','primary'))+
    `<div class="filter-bar"><select data-filter="status" aria-label="Filtrar situação da vistoria"><option value="">Todas as situações</option>${['SOLICITADA','AGENDADA','RECEBIDA'].map(s=>`<option value="${s}" ${filters.status===s?'selected':''}>${labelStatus[s]}</option>`).join('')}</select><span class="filter-count">${list.length} solicitações</span></div>`+
    table(['Talhão','Motivo da vistoria','Prazo','Solicitante','Situação','Arquivos',''],list.map(v=>`<tr><td><strong>${esc(v.codigo)}</strong></td><td style="max-width:240px;line-height:1.7">${esc(v.motivo)}</td><td>${dateOnly(v.prazo)}</td><td>${esc(v.solicitante)}</td><td>${badge(v.status)}</td><td>${v.arquivos.length} imagem(ns)</td><td>${actionButton('Acompanhar','inspection-detail',v.id,'small')}</td></tr>`),`${list.length} vistorias nesta seleção`)+
    `<div class="notice-inline">Uma imagem recebida fica disponível para análise da equipe. O recebimento do arquivo não valida automaticamente georreferenciamento, cobertura ou conformidade da área.</div>`;
}
function historyPage() {
  const q=filters.q.toLowerCase(),list=state.historico.filter(x=>(!q || [x.descricao,x.ator,x.recurso].join(' ').toLowerCase().includes(q))&&(!filters.de || x.criado_em.slice(0,10)>=filters.de)&&(!filters.ate || x.criado_em.slice(0,10)<=filters.ate));
  return heading('DECISÕES QUE DEIXAM RASTRO','Histórico e evidências','Consulte as ações registradas, sua autoria e os motivos informados.')+
    `<div class="filter-bar"><label class="filter-input">${icon('search')}<input data-filter="q" value="${esc(filters.q)}" placeholder="Buscar evento, recurso ou responsável" aria-label="Buscar histórico"></label><input type="date" data-filter="de" value="${esc(filters.de)}" aria-label="Data inicial"><input type="date" data-filter="ate" value="${esc(filters.ate)}" aria-label="Data final"><span class="filter-count">${list.length} eventos</span></div>`+
    `<div class="panel"><div class="panel-head"><div><h2>Registro da operação</h2><p>Até 500 eventos mais recentes</p></div></div><div class="activity-list">${list.map(x=>`<article class="activity-row"><span class="activity-avatar">${esc(initials(x.ator))}</span><div><strong>${esc(x.descricao)}</strong><p>${esc(x.ator)} · ${esc(x.recurso)}${x.dados.justificativa?`<br>${esc(x.dados.justificativa)}`:''}${x.dados.de?`<br>${esc(labelStatus[x.dados.de])} → ${esc(labelStatus[x.dados.para])}`:''}</p></div><time>${when(x.criado_em)}</time></article>`).join('') || empty('O histórico começa nas próximas ações','Cadastros, revisões, vistorias e decisões serão registrados aqui.')}</div></div>`;
}

function integrationsPage() {
  const data=integrationState || {analises:[],fontes:[]};
  return heading('FONTES E EVIDÊNCIAS','Monitoramento ambiental','Consulte alertas oficiais, preserve as evidências e acompanhe as entregas AWS.')+
    `<section class="kpi-grid">${metric('Análises preservadas',data.analises.length,'','Até 100 resultados recentes','leaf')}${metric('Entregas AWS',data.cloud_entregues || 0,'','Objetos e projeções enviados','file')}${metric('Fila de integração',data.cloud_pendentes || 0,'',data.aws_configurada?'Processamento em segundo plano':'Aguardando configuração AWS','clock',true)}</section>`+
    `<div class="notice-inline">O DETER é um sistema de alertas. Uma consulta sem ocorrências permanece em revisão enquanto a cobertura das demais fontes não estiver completa. Cada análise registra o polígono, a consulta, o hash dos dados e a validade de 24 horas.</div>`+
    table(['Fonte','Disponibilidade'],data.fontes.map(f=>`<tr><td><strong>${esc(f.nome)}</strong></td><td>${esc(f.situacao)}</td></tr>`),'Situação das integrações ambientais')+
    `<div class="section-title"><div><h2>Analisar uma origem</h2><p>Consulta pública às camadas DETER Amazônia e Cerrado, com buffer de 100 metros.</p></div></div>`+
    table(['Talhão','Status atual','Última análise',''],state.talhoes.map(t=>{const last=data.analises.find(a=>a.talhao===t.id);return `<tr><td><strong>${esc(t.codigo)}${t.atributos?.ambiente==='SIMULACAO'?'<em class="sim-label">SIMULAÇÃO</em>':''}</strong><small>${esc(farm(t.fazenda)?.nome)}</small></td><td>${badge(t.status)}</td><td>${last?when(last.criado_em):'Não analisado'}</td><td>${actionButton('Consultar INPE','analyze',t.id,'small')}</td></tr>`;}),'Consultas limitadas a uma a cada cinco minutos por talhão')+
    `<div class="section-title"><div><h2>Histórico de análises</h2></div></div>`+
    table(['Talhão','Resultado','Motivo e evidências','Validade'],data.analises.map(a=>`<tr><td><strong>${esc(a.codigo)}</strong><small>#${a.id} · ${when(a.criado_em)}</small></td><td>${badge(a.status)}</td><td style="max-width:400px;white-space:normal">${esc(a.resultado.motivo)}<small>${a.resultado.alertas?.length || 0} alerta(s) · ${a.resultado.fontes?.length || 0} consultas concluídas</small><a href="/app/analises/${a.id}/">Baixar evidências e GeoJSON</a></td><td>${when(a.valido_ate)}<small>${new Date(a.valido_ate)<new Date()?'Análise vencida':'Prazo de reconsulta'}</small></td></tr>`),'Snapshots preservados no PostgreSQL; arquivamento S3 pela fila AWS');
}

function render() {
  if(!state)return;
  route=location.hash.slice(1) || 'inicio';if(!names[route])route='inicio';
  $('#breadcrumb').textContent=names[route];
  $$('nav [data-route]').forEach(a=>a.classList.toggle('active',a.dataset.route===route));
  $('#sidebar').classList.remove('open');
  const pages={inicio:homePage,talhoes:plotsPage,lotes:lotsPage,produtores:()=>recordsPage('produtores'),fazendas:()=>recordsPage('fazendas'),vistorias:inspectionsPage,historico:historyPage,integracoes:integrationsPage,laboratorio:laboratoryPage,relatorios:reportsPage,guia:guidePage};
  $('#main').innerHTML=pages[route]();
  applyAccess();
}

function modal(title,subtitle,body,footer,form='') {
  const inner=`<header class="modal-header"><div><h2>${esc(title)}</h2><p>${esc(subtitle)}</p></div><button class="icon-button" type="button" data-action="close-modal" aria-label="Fechar">${icon('close')}</button></header><div class="modal-body"><div id="form-error" class="form-error" role="alert"></div>${body}</div>${footer?`<footer class="modal-footer">${footer}</footer>`:''}`;
  $('#modal-content').innerHTML=form?`<form id="${form}">${inner}</form>`:inner;
  if(!$('#modal').open)$('#modal').showModal();
  applyAccess();
}
const cancel = '<button class="button" type="button" data-action="close-modal">Cancelar</button>';
const save = text => `<button class="button primary" type="submit">${esc(text)}</button>`;
const inputField=(name,label,type='text',value='',extra='')=>`<label class="field">${esc(label)}<input name="${name}" type="${type}" value="${esc(value)}" ${extra}></label>`;
const selectField=(name,label,options,value='',extra='')=>`<label class="field">${esc(label)}<select name="${name}" aria-label="${esc(label)}" ${extra}>${options.map(([key,text])=>`<option value="${esc(key)}" ${String(value)===String(key)?'selected':''}>${esc(text)}</option>`).join('')}</select></label>`;
function recordForm(kind,id=null) {
  if(!id && kind==='talhoes' && !state.fazendas.length){location.hash='fazendas';toast('Cadastre uma fazenda antes de adicionar seu primeiro talhão.');return;}
  if(!id && kind==='fazendas' && !state.produtores.length){location.hash='produtores';toast('Cadastre um produtor antes de adicionar sua primeira fazenda.');return;}
  const current=id ? state[kind].find(x=>x.id===Number(id)) : {},x=current || {};
  let fields='';
  if(kind==='produtores')fields=inputField('nome','Nome completo','text',x.nome,'required maxlength="200"')+inputField('documento','CPF / CNPJ','text',RaizesDocumento.mask(x.documento || ''),`required maxlength="18" data-documento autocomplete="off" spellcheck="false" placeholder="000.000.000-00 ou 00.000.000/0000-00" ${x.simulado?'readonly':''}`)+inputField('municipio','Município','text',x.municipio,'required')+selectField('uf','UF', [['','Selecione a UF'], ...'AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO'.split(' ').map(uf=>[uf,uf])],x.uf,'required');
  if(kind==='fazendas')fields=inputField('nome','Nome da fazenda','text',x.nome,'required')+selectField('produtor','Produtor responsável',state.produtores.map(p=>[p.id,p.nome]),x.produtor,'required')+inputField('car_codigo','Código CAR','text',x.car_codigo)+inputField('area_ha','Área total (ha)','number',x.area_ha,'required min="0.01" step="0.01"')+inputField('municipio','Município','text',x.municipio,'required')+selectField('uf','UF', [['','Selecione a UF'], ...'AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO'.split(' ').map(uf=>[uf,uf])],x.uf,'required');
  if(kind==='talhoes')fields=inputField('codigo','Código do talhão','text',x.codigo,'required maxlength="40"')+selectField('fazenda','Fazenda de origem',state.fazendas.map(f=>[f.id,f.nome]),x.fazenda,'required')+inputField('cultura','Cultura','text',x.cultura,'required')+inputField('area_ha','Área do talhão (ha)','number',x.area_ha,'required min="0.01" step="0.01"')+
    (!id?selectField('status','Situação inicial',[['REVISAO','Em revisão']], 'REVISAO'):'')+
    selectField('atributo_bioma','Bioma',[['','Não informado'],['cerrado','Cerrado'],['amazonia','Amazônia'],['mata_atlantica','Mata Atlântica'],['caatinga','Caatinga'],['pampa','Pampa'],['pantanal','Pantanal']],x.atributos?.bioma || '')+
    inputField('atributo_fonte','Fonte ambiental informada','text',x.atributos?.fonte || '')+
    inputField('atributo_ndvi','NDVI informado','number',x.atributos?.ndvi ?? '','min="-1" max="1" step="0.01"')+
    `<label class="field full">Importar polígono<input id="geometry-file" type="file" accept=".geojson,.json,.kml"><small>GeoJSON ou KML, até 5 MB. ${Object.keys(x.poligono || {}).length?'Já existe uma geometria cadastrada. Importe outro arquivo para substituí-la.':'Você pode cadastrar a área em revisão e completar a geometria depois.'}</small></label><details class="advanced-field"><summary>Editar coordenadas GeoJSON</summary><label class="field">Geometria<textarea name="poligono" rows="4" placeholder='{"type":"Polygon","coordinates":[...] }'>${esc(JSON.stringify(x.poligono || {},null,2))}</textarea><small>Coordenadas WGS84 na ordem longitude, latitude.</small></label></details><details class="advanced-field"><summary>Outros atributos da origem</summary><label class="field">Atributos adicionais (JSON)<textarea name="atributos" rows="3">${esc(JSON.stringify(x.atributos || {},null,2))}</textarea><small>Preserva metadados flexíveis e identificadores de alertas da origem. As fontes informadas não são consultadas automaticamente.</small></label></details>`;
  modal(`${id?'Editar':'Cadastrar'} ${kind==='produtores'?'produtor':kind==='fazendas'?'fazenda':'talhão'}`,'Os dados serão salvos no cadastro da cooperativa.',`<div class="form-grid">${fields}</div>`,cancel+save('Salvar cadastro'),'record-form');
  $('#record-form').dataset.kind=kind;if(id)$('#record-form').dataset.id=id;
}
function openPlot(id) {
  const t=plot(id);if(!t)return;selectedTalhao=t.id;
  const f=farm(t.fazenda),p=producer(f?.produtor),events=state.historico.filter(e=>e.recurso_id===t.id&&e.recurso==='talhao');
  $('#drawer').innerHTML=`<header class="drawer-head"><div><span class="eyebrow">ORIGEM CADASTRADA</span><h2>${esc(t.codigo)}</h2>${badge(t.status)}<p>${esc(f?.nome)} · ${esc(f?.municipio)} / ${esc(f?.uf)}</p></div><button class="icon-button" data-action="close-drawer" aria-label="Fechar detalhes">${icon('close')}</button></header><div class="drawer-content"><div class="map-wrap drawer-map">${mapSVG([t],plotBounds([t],.45),false,true)}</div><div class="details-grid"><div><span class="detail-label">Produtor responsável</span><span class="detail-value">${esc(p?.nome)}</span></div><div><span class="detail-label">Cultura</span><span class="detail-value">${esc(t.cultura)}</span></div><div><span class="detail-label">Área cadastrada</span><span class="detail-value">${number(t.area_ha,2)} ha</span></div><div><span class="detail-label">Última alteração</span><span class="detail-value">${when(t.atualizado_em)}</span></div></div><div class="drawer-actions">${actionButton('Editar cadastro','edit-record',t.id,'small').replace('data-id=','data-kind="talhoes" data-id=')}${t.status!=='APROVADO'?actionButton('Revisar status','review',t.id,'small primary'):''}${t.status==='REVISAO'?actionButton('Solicitar vistoria','inspection',t.id,'small'):''}<a class="button small" href="/app/exportar/talhao/${t.id}/">${icon('file')}Exportar registro</a></div><section class="drawer-section"><h3>Atributos e fontes informadas</h3>${Object.entries(t.atributos).map(([k,v])=>`<div class="attribute"><span>${esc(k)}</span><span>${esc(Array.isArray(v)?v.join(', ') || 'Nenhum':typeof v==='object'?JSON.stringify(v):v)}</span></div>`).join('') || '<p class="muted">Nenhum atributo cadastrado.</p>'}</section><section class="drawer-section"><h3>Histórico deste talhão</h3><ul class="timeline">${events.slice(0,10).map(x=>`<li><strong>${esc(x.descricao)}</strong><small>${esc(x.ator)} · ${when(x.criado_em)}</small>${x.dados.justificativa?`<p>${esc(x.dados.justificativa)}</p>`:''}</li>`).join('') || '<li><strong>Nenhum evento posterior ao início da trilha.</strong><small>As próximas ações serão registradas.</small></li>'}</ul></section></div>`;
  $('#drawer').hidden=false;$('#drawer-backdrop').hidden=false;
}
function closeDrawer(){selectedTalhao=null;$('#drawer').hidden=true;$('#drawer-backdrop').hidden=true;}
function reviewForm(id) {
  const t=plot(id);closeDrawer();
  modal('Revisar status do talhão',`${t.codigo} · ${farm(t.fazenda)?.nome}`,
    `<div class="notice-inline">O status atual é ${esc(labelStatus[t.status])}. A evidência original e a justificativa desta decisão serão preservadas.</div><div class="form-grid">${selectField('status','Resultado da revisão',Object.entries(labelStatus).slice(0,3).map(([a,b])=>[a,b]),t.status)}<label class="field full">Justificativa da decisão<textarea name="justificativa" required minlength="10" placeholder="Descreva as evidências analisadas e o motivo da decisão."></textarea></label></div>`,cancel+save('Registrar revisão'),'review-form');
  $('#review-form').dataset.id=id;
}
function inspectionForm(id) {
  const t=plot(id);closeDrawer();
  modal('Solicitar vistoria por drone',`${t.codigo} · ${farm(t.fazenda)?.nome}`,
    `<div class="form-grid">${inputField('prazo','Prazo para a vistoria','date',new Date().toISOString().slice(0,10),'required')}<label class="field full">Motivo da solicitação<textarea name="motivo" required minlength="10" placeholder="O que a equipe de campo deve investigar nesta área?"></textarea></label></div><p class="form-hint">Uma solicitação aberta para o mesmo talhão será reutilizada. A vistoria apoia a análise humana e não substitui o monitoramento ambiental.</p>`,cancel+save('Criar solicitação'),'inspection-form');
  $('#inspection-form').dataset.id=id;
}
function chooseInspection() {
  const choices=state.talhoes.filter(t=>t.status==='REVISAO');
  if(!choices.length){toast('Nenhum talhão em revisão está disponível para uma vistoria.');return;}
  modal('Escolha o talhão','Somente origens em revisão podem receber uma solicitação.',`<div class="form-grid">${selectField('talhao','Talhão em revisão',choices.map(t=>[t.id,t.codigo+' · '+farm(t.fazenda)?.nome]))}</div>`,cancel+save('Continuar'),'choose-inspection-form');
}
function inspectionDetails(id) {
  const v=state.vistorias.find(x=>x.id===Number(id));
  modal(`Vistoria #${v.id}`,`${v.codigo} · prazo ${dateOnly(v.prazo)}`,
    `${badge(v.status)}<p class="muted">${esc(v.motivo)}</p><p class="form-hint">Solicitada por ${esc(v.solicitante)} em ${when(v.criado_em)}.</p><section class="drawer-section"><h3>Imagens recebidas</h3>${v.arquivos.map(a=>`<div class="attribute"><a href="${a.url}">${icon('file')}${esc(a.nome)}</a><span>${number(a.tamanho/1024,1)} KB</span></div><p class="form-hint" style="overflow-wrap:anywhere">SHA-256: ${a.sha256}</p>`).join('') || '<p class="muted">Nenhuma imagem recebida.</p>'}</section><div class="notice-inline">Receber o arquivo não aprova sua validade geoespacial. A conferência de georreferenciamento, data e cobertura deve ser concluída pela equipe antes de utilizá-lo como evidência.</div><label class="field upload-zone">Adicionar imagem da vistoria<input name="arquivo" type="file" accept="image/jpeg,image/png,image/tiff,.tif,.tiff" required><small>JPEG, PNG ou TIFF · limite desta implantação: 20 MB.</small></label>`,
    `${v.status==='SOLICITADA'?actionButton('Marcar como agendada','schedule-inspection',id):''}${cancel}${save('Enviar imagem')}`,'upload-form');
  $('#upload-form').dataset.id=id;
}
function receiveForm() {
  receiptItems=[{talhao:state.talhoes[0]?.id,peso_kg:''}];
  modal('Receber lote na balança','Informe o peso total e distribua o peso entre as origens.',`<div class="form-grid">${inputField('codigo','Número do lote / romaneio','text','','required maxlength="40"')}${inputField('peso_total_kg','Peso total (kg)','number','','required min="0.01" step="0.01"')}</div><section class="drawer-section"><h3>Talhões de origem</h3><div id="receipt-origins"></div><button class="button text" type="button" data-action="add-origin">${icon('plus')}Adicionar outra origem</button><div class="weight-total"><span>Peso distribuído</span><strong id="distributed-weight">0 kg</strong></div></section><p class="form-hint">O sistema consulta as origens e atribui ao lote o pior status. Peso divergente ou talhão repetido interrompem toda a gravação.</p>`,cancel+save('Consultar origens e receber'),'receive-form');
  renderOrigins();
}
function captureOrigins() {receiptItems=$$('.receipt-origin').map(el=>({talhao:Number($('select',el).value),peso_kg:$('input',el).value}));}
function renderOrigins() {
  $('#receipt-origins').innerHTML=receiptItems.map((x,i)=>`<div class="receipt-origin" data-index="${i}">${selectField('origem','Talhão',state.talhoes.map(t=>[t.id,t.codigo+' · '+labelStatus[t.status]]),x.talhao,'required')}${inputField('peso_origem','Peso (kg)','number',x.peso_kg,'required min="0.01" step="0.01"')}<button class="icon-button" data-action="remove-origin" data-id="${i}" type="button" aria-label="Remover origem">${icon('close')}</button></div>`).join('');
  updateWeight();
}
function updateWeight(){if($('#distributed-weight'))$('#distributed-weight').textContent=number($$('.receipt-origin input').reduce((s,i)=>s+Number(i.value),0),2)+' kg';}
function lotDetails(id,newReceipt=false) {
  const l=lot(id),d=state.decisoes[id];if(!l)return;
  modal(newReceipt?'Origem consultada e lote registrado':'Detalhes do recebimento',l.codigo+(l.simulado?' · SIMULAÇÃO':''),
   `<div class="result-status ${statusClass(l.status)}"><span class="eyebrow">STATUS OPERACIONAL DO LOTE</span><h3>${esc(labelStatus[l.status])}</h3><p>${esc(l.motivo || 'Status informado no cadastro do lote.')}</p></div><div class="details-grid"><div><span class="detail-label">Peso total</span><span class="detail-value">${number(l.peso_total_kg,2)} kg</span></div><div><span class="detail-label">Recebimento</span><span class="detail-value">${when(l.recebido_em)}</span></div></div><section class="drawer-section"><h3>Talhões de origem</h3>${l.itens.map(i=>`<div class="attribute"><span>${esc(i.talhao_codigo)}</span><span>${number(i.peso_kg,2)} kg · ${badge(plot(i.talhao)?.status || l.status)}</span></div>`).join('') || '<p class="muted">Nenhuma origem associada.</p>'}</section>${d?`<section class="drawer-section"><h3>Decisão registrada: ${d.acao==='ACEITAR'?'aceito':'recusado'}</h3><p class="muted">${esc(d.justificativa)}</p><p class="form-hint">${esc(d.operador)} · ${when(d.criado_em)}</p></section>`:''}`,
   `<a class="button" href="/app/exportar/lote/${id}/">Exportar registro</a><button class="button" data-action="close-modal">Fechar</button>${!d?actionButton('Registrar decisão','decision',id,'primary'):''}`);
}
function decisionForm(id) {
  const l=lot(id);
  modal('Registrar decisão na balança',l.codigo,`<div class="notice-inline">Status de origem: ${esc(labelStatus[l.status])}. A decisão ficará vinculada a você e ao status consultado, sem edição posterior.</div><div class="form-grid">${selectField('acao','Decisão do operador',l.status==='APROVADO'?[['ACEITAR','Aceitar recebimento'],['RECUSAR','Recusar recebimento']]:[['RECUSAR','Recusar recebimento']])}<label class="field full">Justificativa<textarea name="justificativa" required minlength="10" placeholder="Registre o motivo e as verificações realizadas."></textarea></label></div>`,cancel+save('Confirmar decisão'),'decision-form');
  $('#decision-form').dataset.id=id;
}

document.addEventListener('click',async event=>{
  const el=event.target.closest('[data-action]');
  if(!el) {if(event.target.closest('nav [data-route]'))$('#sidebar').classList.remove('open');const row=event.target.closest('[data-talhao]');if(row)openPlot(row.dataset.talhao);return;}
  event.preventDefault();event.stopPropagation();
  const action=el.dataset.action,id=el.dataset.id;
  try {
    if(action==='new-talhao')recordForm('talhoes');
    if(action==='new-record')recordForm(el.dataset.kind);
    if(action==='edit-record'){closeDrawer();recordForm(el.dataset.kind,id);}
    if(action==='detail')openPlot(id);
    if(action==='analyze'){
      el.disabled=true;el.textContent='Consultando fontes…';
      try {await api(`/app/talhoes/${id}/analisar/`,'POST',{});await refresh();toast('Análise registrada. Consulte o motivo e as evidências.');}
      finally {if(el.isConnected){el.disabled=false;el.textContent='Consultar INPE';}}
    }
    if(action==='close-drawer')closeDrawer();
    if(action==='close-modal'){$('#modal').close();if(el.tagName==='A' && el.hash)location.hash=el.hash;}
    if(action==='review')reviewForm(id);
    if(action==='inspection')inspectionForm(id);
    if(action==='choose-inspection')chooseInspection();
    if(action==='inspection-detail')inspectionDetails(id);
    if(action==='receive')receiveForm();
    if(action==='lot-detail')lotDetails(id);
    if(action==='decision')decisionForm(id);
    if(action==='add-origin'){captureOrigins();receiptItems.push({talhao:state.talhoes[0]?.id,peso_kg:''});renderOrigins();}
    if(action==='remove-origin'){captureOrigins();if(receiptItems.length===1){toast('O lote precisa de pelo menos uma origem.');return;}receiptItems.splice(Number(id),1);renderOrigins();}
    if(action==='schedule-inspection'){await api(`/app/vistorias/${id}/status/`,'POST',{status:'AGENDADA'});await refresh();inspectionDetails(id);toast('Vistoria marcada como agendada.');}
    if(action==='delete-record'){
      const kind=el.dataset.kind,x=state[kind].find(x=>x.id===Number(id));
      modal('Excluir cadastro',x.nome || x.codigo,`<p class="muted">Deseja excluir este cadastro? Registros com referências ativas não podem ser removidos.</p>`,cancel+`<button class="button danger" data-action="confirm-delete" data-kind="${kind}" data-id="${id}">Confirmar exclusão</button>`);
    }
    if(action==='confirm-delete'){await api(`/api/${el.dataset.kind}/${id}/`,'DELETE');$('#modal').close();await refresh();toast('Cadastro excluído.');}
    if(action.startsWith('map-')){
      const plots=route==='talhoes'?filteredPlots():state.talhoes;
      if(action==='map-fit')mapBounds=plotBounds(plots,.3);
      if(action==='map-reset')mapBounds=null;
      if(action==='map-cluster')mapBounds=plotBounds(id.split(',').map(plot),.8);
      if(['map-zoom-in','map-zoom-out'].includes(action)){
        const b=mapBounds || [-74,-34,-34,6],factor=action==='map-zoom-in'?.58:1.7,cx=(b[0]+b[2])/2,cy=(b[1]+b[3])/2,dx=(b[2]-b[0])*factor/2,dy=(b[3]-b[1])*factor/2;
        mapBounds=[cx-dx,cy-dy,cx+dx,cy+dy];
      }
      render();
    }
  } catch(error) {if($('#modal').open && $('#form-error'))$('#form-error').textContent=error.message;else toast(error.message,true);}
});

document.addEventListener('submit',async event=>{
  const form=event.target;if(!form.id || !form.id.endsWith('-form'))return;
  event.preventDefault();const data=Object.fromEntries(new FormData(form));
  const button=event.submitter || $('button[type=submit]',form);if(button)button.disabled=true;
  try {
    if(form.id==='record-form'){
      const kind=form.dataset.kind,id=form.dataset.id;
      if(data.uf)data.uf=data.uf.toUpperCase();
      if(kind==='produtores' && data.documento!=='DEMO-RAIZES') {
        if(!RaizesDocumento.valid(data.documento))throw new Error('Confira o CPF/CNPJ e os dígitos verificadores.');
        data.documento=RaizesDocumento.clean(data.documento);
      }
      if(kind==='talhoes'){
        try{data.poligono=JSON.parse(data.poligono || '{}');data.atributos=JSON.parse(data.atributos || '{}');}
        catch{throw new Error('Confira o JSON do polígono e dos atributos: há um erro de formato.');}
        if(Array.isArray(data.atributos) || !data.atributos || typeof data.atributos!=='object')throw new Error('Os atributos devem ser um objeto JSON.');
        for(const [field,key] of [['atributo_bioma','bioma'],['atributo_fonte','fonte'],['atributo_ndvi','ndvi']]){
          if(data[field] !== '')data.atributos[key]=key==='ndvi'?Number(data[field]):data[field];
          else delete data.atributos[key];
          delete data[field];
        }
        validateGeometry(data.poligono);
      }
      await api(`/api/${kind}/${id?id+'/':''}`,id?'PATCH':'POST',data);$('#modal').close();await refresh();toast('Cadastro salvo com sucesso.');
    }
    if(form.id==='review-form'){await api(`/app/talhoes/${form.dataset.id}/revisar/`,'POST',data);$('#modal').close();await refresh();openPlot(form.dataset.id);toast('Revisão registrada com justificativa e autoria.');}
    if(form.id==='inspection-form'){const result=await api(`/app/talhoes/${form.dataset.id}/vistoria/`,'POST',data);$('#modal').close();await refresh();location.hash='vistorias';toast(result.existente?'Já havia uma solicitação aberta para este talhão.':'Vistoria solicitada.');}
    if(form.id==='choose-inspection-form'){inspectionForm(data.talhao);}
    if(form.id==='receive-form'){
      captureOrigins();data.itens=receiptItems;const result=await api('/api/lotes/receber/','POST',data);await refresh();lotDetails(result.id,true);toast('Lote e origens registrados em uma única transação.');
    }
    if(form.id==='decision-form'){await api(`/app/lotes/${form.dataset.id}/decisao/`,'POST',data);await refresh();lotDetails(form.dataset.id);toast('Decisão preservada no histórico da operação.');}
    if(form.id==='upload-form'){await api(`/app/vistorias/${form.dataset.id}/arquivo/`,'POST',new FormData(form));await refresh();inspectionDetails(form.dataset.id);toast('Imagem recebida e hash registrado. Validação geoespacial pendente.');}
  } catch(error) {const target=$('#form-error');if(target)target.textContent=error.message;else toast(error.message,true);}
  finally {if(button?.isConnected)button.disabled=false;}
});

function validateGeometry(geometry) {
  if(!Object.keys(geometry).length)return;
  if(!['Polygon','MultiPolygon'].includes(geometry.type) || !Array.isArray(geometry.coordinates))throw new Error('Use uma geometria GeoJSON Polygon ou MultiPolygon.');
  for(const ring of rings(geometry)){
    if(ring.length<4)throw new Error('Cada anel do polígono precisa de pelo menos quatro coordenadas.');
    if(JSON.stringify(ring[0])!==JSON.stringify(ring[ring.length-1]))throw new Error('O polígono deve ser fechado: a primeira e a última coordenadas precisam coincidir.');
    if(ring.some(p=>!Array.isArray(p)||p.length<2||!Number.isFinite(p[0])||!Number.isFinite(p[1])||p[0]<-74||p[0]>-34||p[1]<-34||p[1]>6))throw new Error('Use coordenadas WGS84 de uma área no Brasil, na ordem longitude, latitude.');
  }
}
document.addEventListener('change',async event=>{
  if(event.target.id==='geometry-file'){
    const file=event.target.files[0];if(!file)return;
    try{
      if(file.size>5*1024*1024)throw new Error('O arquivo de geometria deve ter no máximo 5 MB.');
      const text=await file.text();let geometry;
      if(file.name.toLowerCase().endsWith('.kml')){
        const doc=new DOMParser().parseFromString(text,'application/xml');
        if(doc.querySelector('parsererror'))throw new Error('O arquivo KML contém um erro de formato.');
        const polygons=[...doc.getElementsByTagNameNS('*','Polygon')];
        const parsed=polygons.map(p=>[...p.getElementsByTagNameNS('*','LinearRing')].map(r=>r.getElementsByTagNameNS('*','coordinates')[0]?.textContent.trim().split(/\s+/).map(c=>c.split(',').slice(0,2).map(Number))));
        if(!parsed.length)throw new Error('Nenhum polígono foi encontrado no KML.');
        geometry=parsed.length===1?{type:'Polygon',coordinates:parsed[0]}:{type:'MultiPolygon',coordinates:parsed};
      }else{
        const parsed=JSON.parse(text);geometry=parsed.type==='Feature'?parsed.geometry:parsed.type==='FeatureCollection'?{type:'MultiPolygon',coordinates:parsed.features.flatMap(f=>f.geometry.type==='Polygon'?[f.geometry.coordinates]:f.geometry.coordinates)}:parsed;
      }
      validateGeometry(geometry);$('#record-form [name=poligono]').value=JSON.stringify(geometry,null,2);toast('Geometria importada. Confira os dados e salve o cadastro.');
    }catch(error){$('#form-error').textContent=error.message;}
  }
  if(event.target.matches('[data-filter]:not(input[data-filter="q"])')){filters[event.target.dataset.filter]=event.target.value;render();}
});
let searchTimer;
document.addEventListener('input',event=>{
  if(event.target.closest('.receipt-origin'))updateWeight();
  if(event.target.matches('input[data-filter="q"]')){
    clearTimeout(searchTimer);const caret=event.target.selectionStart;
    searchTimer=setTimeout(()=>{filters.q=event.target.value;render();const input=$('input[data-filter="q"]');if(input){input.focus();input.setSelectionRange(caret,caret);}},220);
  }
});
$('#global-search').addEventListener('keydown',event=>{if(event.key==='Enter'){filters={q:event.target.value,status:'',municipio:'',produtor:'',de:'',ate:''};preserveFiltersOnHash=location.hash!=='#talhoes';location.hash='talhoes';render();}});
$('#mobile-menu').addEventListener('click',()=>$('#sidebar').classList.toggle('open'));
$('#drawer-backdrop').addEventListener('click',closeDrawer);
document.addEventListener('keydown',event=>{if(event.key==='Escape')closeDrawer();if(event.key==='Enter'&&event.target.matches('.marker'))event.target.dispatchEvent(new MouseEvent('click',{bubbles:true}));});
$('#notifications').addEventListener('click',()=>{
  modal('Atualizações da operação','As ações mais recentes registradas pela equipe.',`<ul class="timeline">${state.historico.slice(0,8).map(x=>`<li><strong>${esc(x.descricao)}</strong><small>${esc(x.ator)} · ${when(x.criado_em)}</small></li>`).join('') || '<li><strong>Nenhuma atualização registrada ainda.</strong></li>'}</ul>`,`<a href="#historico" class="button primary" data-action="close-modal">Ver histórico</a>`);
});
window.addEventListener('hashchange',()=>{if(!preserveFiltersOnHash)filters={q:'',status:'',municipio:'',produtor:'',de:'',ate:''};preserveFiltersOnHash=false;mapBounds=null;closeDrawer();render();window.scrollTo(0,0);});
window.matchMedia('(max-width:720px)').addEventListener('change',()=>render());
(async()=>{
  try {const response=await fetch('/static/raizes/brasil.geojson');brazil=await response.json();await refresh();}
  catch(error){$('#connection-label').textContent='Conexão indisponível';$('#main').innerHTML=heading('NÃO FOI POSSÍVEL CARREGAR','Vamos tentar novamente?',error.message)+`<button class="button primary" onclick="location.reload()">Tentar novamente</button>`;}
})();
