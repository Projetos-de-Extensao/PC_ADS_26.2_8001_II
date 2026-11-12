/* Academic lab: persistent synthetic scenarios, never presented as real observations. */
'use strict';
let laboratorioState=null,reportState=null,selectedRun=null,labSending=false,labPaused=false;
const can=cap=>Boolean(state?.usuario?.capacidades?.includes(cap));
function labRequestId(){
  const bytes=crypto.getRandomValues(new Uint8Array(16));bytes[6]=(bytes[6]&15)|64;bytes[8]=(bytes[8]&63)|128;
  const h=Array.from(bytes,b=>b.toString(16).padStart(2,'0')).join('');
  return `${h.slice(0,8)}-${h.slice(8,12)}-${h.slice(12,16)}-${h.slice(16,20)}-${h.slice(20)}`;
}

function applyAccess(){
  document.querySelectorAll('[data-action="lot-detail"]').forEach(el=>{
    const record=lot(el.dataset.id),title=el.closest('tr')?.querySelector('td strong');
    if(record?.simulado&&title&&!title.querySelector('.sim-label')){
      const label=document.createElement('em');label.className='sim-label';label.textContent='SIMULAÇÃO';title.append(label);
    }
  });
  document.querySelectorAll('[data-action]').forEach(el=>{
    const action=el.dataset.action;
    const caps={review:'analise',analyze:'analise',inspection:'analise','choose-inspection':'analise',
      'new-talhao':'cadastros','new-record':'cadastros','edit-record':'cadastros','delete-record':'cadastros',
      'confirm-delete':'cadastros',receive:'balanca',decision:'balanca','schedule-inspection':'campo'};
    if(caps[action]&&!can(caps[action]))el.hidden=true;
  });
  document.querySelectorAll('a[href^="/app/exportar/"],a[href="/app/relatorios/exportar/"]').forEach(el=>el.hidden=!can('exportar'));
  const upload=document.querySelector('#upload-form');
  if(upload&&!can('campo')){upload.querySelector('[name=arquivo]').disabled=true;upload.querySelector('button[type=submit]').hidden=true;}
}

function laboratoryPage(){
  const data=laboratorioState || {cenarios:[],execucoes:[]};
  const run=data.execucoes.find(r=>r.id===selectedRun) || data.execucoes[0];
  if(run)selectedRun=run.id;
  return heading('APRENDER EXPERIMENTANDO','Laboratório de demonstração','Execute o fluxo completo com dados fictícios, sem precisar de satélite, sensor ou drone físico.')+
    `<div class="notice-inline"><strong>AMBIENTE SIMULADO.</strong> Os nomes DETER, MapBiomas e Sentinel identificam os papéis das fontes no exercício. Os dados destes cenários são sintéticos. S3, DynamoDB e a fila AWS continuam sendo serviços reais.</div>`+
    `<div class="lab-scenarios">${data.cenarios.map(c=>`<article class="panel lab-scenario"><span class="eyebrow">CENÁRIO VIRTUAL</span><h2>${esc(c.nome)}</h2><p>${esc(c.descricao)}</p>${can('laboratorio')?`<button class="button" data-lab="create" data-case="${c.id}">Executar cenário</button>`:'<small>Execução disponível ao analista ou gestor.</small>'}</article>`).join('')}</div>`+
    `<section class="section-title"><div><h2>Execuções preservadas</h2><p>Selecione uma execução para inspecionar as evidências e simular uma vistoria.</p></div></section>`+
    `<div class="lab-run-list">${data.execucoes.map(r=>`<button class="button ${r.id===selectedRun?'primary':''}" data-lab="select" data-id="${r.id}">${esc(r.codigo)} · ${esc(data.cenarios.find(c=>c.id===r.cenario)?.nome || r.cenario)}</button>`).join('') || empty('Nenhum cenário criado','Execute um dos cenários acima para iniciar a apresentação.')}</div>`+
    (run?runDetails(run):'');
}

function runDetails(run){
  const t=plot(run.talhao),result=run.dados.resultado,upload=run.uploads[0];
  if(!t)return '';
  const hasValid=run.uploads.some(u=>u.status==='VALIDADO');
  return `<section class="panel lab-detail"><div class="panel-head"><div><h2>${esc(run.codigo)} · dados simulados</h2><p>${when(run.criado_em)}</p></div>${badge(run.status)}</div><div class="lab-detail-body"><div class="lab-flow"><span>1 · Talhão fictício</span><span>2 · Fontes sintéticas</span><span>3 · Análise espacial</span><span>4 · Status e evidência</span><span>5 · Fila AWS</span></div><p class="lab-reason"><strong>Resultado original: </strong>${esc(result.motivo)}</p>
    <div class="lab-two"><div class="map-wrap">${mapSVG([t],plotBounds([t],.45),false,true)}<p class="form-hint">Polígono e alertas deste cenário são fictícios.</p></div><div><h3>O que foi consultado no exercício?</h3><ul class="lab-facts">${result.fontes.map(f=>`<li><strong>${esc(f.fonte)}</strong><span>${esc(f.situacao)} · simulado</span></li>`).join('')}<li><strong>NDVI sintético</strong><span>${result.sentinel.ndvi ?? 'Não utilizável por nuvens'}</span></li><li><strong>Nuvens</strong><span>${result.sentinel.nuvens_percentual}%</span></li><li><strong>Alertas espaciais</strong><span>${result.alertas.length}</span></li></ul><p class="form-hint">NDVI = (NIR − vermelho) / (NIR + vermelho). Um NDVI alto não elimina um alerta de desmatamento.</p><a class="button small" href="/app/analises/${run.dados.analise}/">Baixar evidência sintética</a></div></div>
    <div class="drawer-section"><h3>Vistoria por drone virtual</h3><p class="muted">O voo gera uma área coberta e uma data fictícias. O sistema calcula a interseção com o talhão e confere cobertura mínima de 95%. Receber um voo válido permite a revisão humana; não muda o status sozinho.</p>
    ${run.status==='REVISAO'&&can('campo')&&!run.uploads.some(u=>u.status==='EM_ENVIO')?`<div class="lab-flight-controls"><label class="field">Tipo de voo<select id="lab-flight-profile"><option value="valido">Voo válido · cobertura de 98%</option><option value="cobertura_insuficiente">Cobertura insuficiente · 60%</option><option value="antigo">Voo anterior à análise</option><option value="sem_georreferencia">Sem georreferência</option></select></label><button class="button" data-lab="flight" data-id="${run.id}">Iniciar voo virtual</button></div>`:''}
    ${upload?uploadDetails(upload):'<p class="form-hint">Crie uma vistoria para uma origem em revisão e acompanhe o envio virtual.</p>'}
    ${run.status==='REVISAO'&&hasValid&&can('analise')?`<button class="button primary" data-action="review" data-id="${t.id}">Revisar status com a vistoria</button>`:''}
    </div><div class="drawer-actions">${actionButton('Ver talhão','detail',t.id,'small')}<a class="button small" href="/app/exportar/talhao/${t.id}/">Exportar dossiê com hashes</a><a class="button small" href="#lotes">Abrir balança</a></div></div></section>`;
}

function uploadDetails(u){
  const percent=Math.round(u.partes.length/u.total_partes*100),valid=u.validacao;
  return `<section class="lab-upload" aria-live="polite"><div class="lab-upload-head"><strong>Envio virtual · ${esc(u.status)}</strong><span>${u.partes.length}/${u.total_partes} partes</span></div><div class="lab-progress" role="progressbar" aria-label="Partes do envio virtual" aria-valuenow="${percent}" aria-valuemin="0" aria-valuemax="100"><span style="width:${percent}%"></span></div><p class="form-hint">5 GiB declarados em metadados. <strong>0 bytes de imagem transferidos.</strong> A simulação demonstra divisão em partes e retomada, sem testar transferência ou desempenho de um arquivo real de 5 GiB.</p>
    ${u.status==='EM_ENVIO'&&can('campo')?`<div class="drawer-actions"><button class="button" data-lab="send" data-count="3" data-id="${u.id}" ${labSending?'disabled':''}>Enviar próximas 3 partes</button><button class="button" data-lab="send" data-count="10" data-id="${u.id}" ${labSending?'disabled':''}>${u.partes.length?'Retomar envio':'Enviar todas as partes'}</button><button class="button" data-lab="pause" ${labSending?'':'disabled'}>Pausar</button><button class="button text" data-lab="cancel" data-id="${u.id}" ${labSending?'disabled':''}>Cancelar envio</button>${u.partes.length===u.total_partes?`<button class="button primary" data-lab="finish" data-id="${u.id}">Validar voo</button>`:''}</div>`:''}
    ${valid.sha256?`<div class="notice-inline"><strong>${valid.apto_para_revisao?'Voo virtual apto para revisão':'Voo virtual rejeitado'}</strong><p>Cobertura calculada: ${number(valid.cobertura_percentual,2)}% · data ${dateOnly(u.data_voo)}</p>${valid.erros.map(e=>`<p>${esc(e)}</p>`).join('')}<p class="form-hint" style="overflow-wrap:anywhere">SHA-256 do manifesto: ${esc(valid.sha256)}</p><a href="${u.url}" target="_blank" rel="noopener">Abrir desenho esquemático da cobertura ↗</a></div>`:''}</section>`;
}

function reportsPage(){
  const data=reportState || {linhas:[],entregas:[]};
  return heading('DADOS PARA A APRESENTAÇÃO','Relatórios e integrações','Compare origens e acompanhe os eventos enviados pela aplicação.',can('exportar')?'<a class="button" href="/app/relatorios/exportar/">Exportar CSV</a>':'')+
    `<div class="notice-inline">Os agrupamentos abaixo são calculados no PostgreSQL. Na arquitetura-alvo, Athena consultaria o histórico no S3; nenhuma consulta Athena é simulada como execução real.</div>`+
    table(['Ambiente','Município','Status','Talhões','Área'],data.linhas.map(x=>`<tr><td>${x.ambiente==='SIMULACAO'?'<span class="status review">Simulação</span>':'Operacional'}</td><td>${esc(x.municipio)}</td><td>${badge(x.status)}</td><td>${x.talhoes}</td><td>${number(x.area_ha,2)} ha</td></tr>`),'Agrupamentos SQL sobre os registros persistidos')+
    `<section class="section-title"><div><h2>Fila de entregas AWS</h2><p>Até 50 eventos recentes; o worker tenta novamente os que falham.</p></div></section>`+
    table(['Evento','Destino','Estado','Tentativas','Referência'],data.entregas.map(e=>`<tr><td>#${e.id}<small>${when(e.criado_em)}</small></td><td>${{EVIDENCIA:'S3',STATUS:'DynamoDB',ALERTA:'SNS'}[e.tipo] || esc(e.tipo)}</td><td>${esc(e.estado)}${e.erro?`<small>${esc(e.erro)}</small>`:''}</td><td>${e.tentativas}</td><td style="overflow-wrap:anywhere;max-width:300px">${esc(e.chave)}</td></tr>`),'S3 e DynamoDB recebem dados reais da aplicação, com marcação dos cenários fictícios');
}

function guidePage(){
  const components=[['Seu navegador','Mostra as telas, envia os formulários e guarda a sessão de login. Não acessa o banco diretamente.'],['EC2 + Docker','A EC2 é o computador virtual na AWS. Docker Compose mantém três containers: web, db e integracoes.'],['Django + Gunicorn','Gunicorn recebe HTTP na porta 8000. Django valida permissões, regras, formulários e APIs e produz as respostas.'],['PostgreSQL','Guarda produtores, fazendas, talhões, lotes, análises e histórico. O volume pgdata mantém os dados após recriar containers.'],['Worker de integrações','Roda fora da requisição da tela. Reconsulta áreas operacionais após 24 h e processa a fila AWS a cada minuto. Não reconsulta cenários virtuais no INPE.'],['S3 · DynamoDB · SNS','S3 guarda evidências; DynamoDB recebe uma projeção do status; SNS publica eventos. Os serviços são reais, mesmo quando o conteúdo é marcado como simulado.']];
  const target=[['API Gateway + Lambda','Hoje representados pela API Django e suas funções de processamento. Não foram provisionados.'],['EventBridge','Hoje o worker Compose faz o agendamento. Não há regra EventBridge nesta implantação.'],['RDS + PostGIS','Hoje PostgreSQL está em container na EC2 e Shapely/PROJ calculam geometrias. RDS e a extensão PostGIS não estão ativos.'],['Cognito + MFA','Hoje há sessão Django e grupos por perfil. Não há Cognito nem MFA; os grupos são verificados também no servidor.'],['Athena + Parquet','Hoje os relatórios usam SQL no PostgreSQL e exportação CSV. Evidências S3 são JSON; Athena e Parquet não estão ativos.'],['Drones e grandes arquivos','O laboratório gera metadados e cobertura geométrica, sem voo físico ou fotografia real. Os 5 GiB são tamanho declarado para exercitar o protocolo virtual.']];
  return heading('GUIA PARA ENTENDER E EXPLICAR','Como o Raízes funciona','Use este roteiro para apresentar o problema, percorrer uma operação e explicar a infraestrutura.')+
    `<section class="panel guide-intro"><span class="eyebrow">O PROBLEMA</span><h2>De qual área veio esta carga?</h2><p>Uma cooperativa recebe produtos de diferentes propriedades. O Raízes conecta cada lote aos talhões de origem, classifica riscos, reúne evidências e registra quem decidiu aceitar ou recusar a carga.</p></section>`+
    `<section class="section-title"><div><h2>Infraestrutura publicada agora</h2></div></section><div class="infra-flow"><span>Navegador</span><span>HTTP :8000 → EC2 / Django</span><span>PostgreSQL + volumes</span><span>Fila → worker → AWS</span></div><div class="guide-grid">${components.map(([title,text])=>`<article class="panel guide-card"><h3>${title}</h3><p>${text}</p></article>`).join('')}</div>`+
    `<section class="section-title"><div><h2>Uma operação, do início ao fim</h2></div></section><ol class="guide-steps"><li><strong>Cadastre a origem.</strong> Produtor → fazenda → talhão. O polígono GeoJSON representa o contorno da área; atributos JSONB armazenam informações flexíveis.</li><li><strong>Analise o risco.</strong> No monitoramento real, a aplicação consulta o INPE/DETER. No laboratório, três fontes sintéticas exercitam as regras de interseção, proximidade, nuvens e indisponibilidade.</li><li><strong>Resolva a dúvida.</strong> Uma área em revisão pode receber vistoria. No laboratório, um voo virtual deve cobrir pelo menos 95% do talhão e ter data válida. Depois o analista decide com justificativa.</li><li><strong>Receba o lote.</strong> Distribua o peso entre os talhões. O lote assume o pior status; peso divergente ou origem repetida faz a transação inteira voltar atrás.</li><li><strong>Decida e preserve.</strong> A balança revalida as origens antes de aceitar. A decisão fica registrada. O dossiê reúne geometrias, análises, auditoria e hashes para conferir integridade.</li></ol>`+
    `<section class="section-title"><div><h2>Por que a fila existe?</h2></div></section><div class="notice-inline">A alteração do domínio e a intenção de envio são gravadas na mesma transação PostgreSQL. O worker entrega depois. Se a AWS falhar, o evento fica pendente para nova tentativa; uma falha de rede não apaga o cadastro nem a análise. DynamoDB é uma cópia de consulta: a balança desta versão usa PostgreSQL.</div>`+
    `<section class="section-title"><div><h2>O desenho completo da documentação</h2><p>Estes serviços explicam a evolução arquitetural, sem aumentar a infraestrutura da demonstração.</p></div></section>`+
    table(['Componente previsto','Como o protótipo representa o papel'],target.map(([a,b])=>`<tr><td><strong>${a}</strong></td><td style="white-space:normal;max-width:560px;line-height:1.8">${b}</td></tr>`),'Papéis equivalentes no protótipo não significam serviços AWS provisionados')+
    `<section class="section-title"><div><h2>Perfis e cuidados de operação</h2></div></section>`+
    table(['Perfil','O que pode fazer'],[['Gestor','Todas as ações da operação.'],['Analista','Cadastros, análises, solicitação de vistoria, revisão e laboratório.'],['Operador da balança','Recebimento e decisão de lotes.'],['Piloto','Agendamento, recebimento de arquivos e voos virtuais.'],['Auditor','Consultas e exportações.']].map(([a,b])=>`<tr><td>${a}</td><td>${b}</td></tr>`),'Seu perfil: '+(state?.usuario?.perfil || 'Equipe'))+
    `<div class="notice-inline">O administrador atribui os grupos aos usuários no Django Admin. Contas antigas de equipe sem grupo conservam acesso amplo para compatibilidade; não há segregação por cooperativa nesta demonstração. Login é necessário para a operação; leituras da API acadêmica continuam públicas. O endereço atual usa HTTP e exige cuidado com dados e credenciais reais.</div><p class="form-hint">O backup PostgreSQL diário permanece local. Foi autorizada uma única cópia ao S3, restaurada em banco separado para validação. S3 versionado não equivale a Object Lock, retenção de cinco anos ou certificação EUDR.</p>`;
}

document.addEventListener('click',async event=>{
  const el=event.target.closest('[data-lab]');if(!el)return;
  event.preventDefault();const action=el.dataset.lab,id=el.dataset.id;
  if(action==='pause'){labPaused=true;toast('Pausa solicitada. As partes concluídas ficam preservadas.');return;}
  el.disabled=true;
  try{
    if(action==='create'){
      const row=await api('/app/laboratorio/executar/','POST',{cenario:el.dataset.case,idempotencia:labRequestId()});
      selectedRun=row.id;await refresh();toast('Cenário fictício criado, com evidências e marcação de simulação.');
    }
    if(action==='select'){selectedRun=id;render();}
    if(action==='flight'){await api(`/app/laboratorio/${id}/voos/`,'POST',{perfil:document.querySelector('#lab-flight-profile').value});await refresh();}
    if(action==='send'){
      labSending=true;labPaused=false;
      let upload=laboratorioState.execucoes.flatMap(r=>r.uploads).find(u=>u.id===id);
      render();let sent=0;
      for(let part=1;part<=upload.total_partes;part++){
        if(labPaused||sent>=Number(el.dataset.count))break;
        if(upload.partes.includes(part))continue;
        upload=await api(`/app/laboratorio/voos/${id}/partes/`,'POST',{parte:part});sent++;
        const parent=laboratorioState.execucoes.find(r=>r.uploads.some(u=>u.id===id));
        parent.uploads=parent.uploads.map(u=>u.id===id?upload:u);render();
      }
      labSending=false;await refresh();toast('Partes virtuais preservadas; você pode sair e retomar depois.');
    }
    if(action==='finish'){await api(`/app/laboratorio/voos/${id}/finalizar/`,'POST',{});await refresh();toast('Validação geométrica concluída. Confira o resultado antes da revisão.');}
    if(action==='cancel'){await api(`/app/laboratorio/voos/${id}/cancelar/`,'POST',{});await refresh();toast('Envio virtual cancelado. O histórico foi preservado.');}
  }catch(error){toast(error.message,true);}
  finally{labSending=false;if(el.isConnected)el.disabled=false;}
});
