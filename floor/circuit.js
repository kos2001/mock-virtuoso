(() => {
'use strict';
const button = document.createElement('button');
button.id = 'circuit-open'; button.type = 'button'; button.className = 'tab';
button.textContent = '회로 · 시뮬레이션'; button.setAttribute('aria-haspopup', 'dialog');
document.querySelector('header').append(button);
const panel = document.createElement('dialog');
panel.id = 'circuit-panel'; panel.setAttribute('aria-labelledby', 'circuit-title');
panel.innerHTML = `
<style>
#circuit-panel{color:var(--ink);background:var(--bg);border:1px solid var(--edge);border-radius:10px;width:min(1120px,94vw);max-height:90vh;overflow:auto;padding:24px;font:14px/1.5 system-ui}
#circuit-panel::backdrop{background:#0009}#circuit-panel [hidden]{display:none!important}
#circuit-panel label{max-width:100%}#circuit-panel input,#circuit-panel select{max-width:100%;box-sizing:border-box}
#circuit-panel td{overflow-wrap:anywhere}
#circuit-panel h1{font-size:22px;margin:0}#circuit-panel h2{font:600 18px system-ui;color:var(--ink);letter-spacing:0;text-transform:none;padding:0}
#circuit-panel .bar{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin:14px 0}
#circuit-panel label{display:flex;flex-direction:column;gap:4px}#circuit-panel button,#circuit-panel input,#circuit-panel select{font:inherit;border:1px solid #40516a;border-radius:5px;background:#192535;color:var(--ink);padding:8px;min-width:0}
#circuit-panel button{cursor:pointer}#circuit-panel button.primary{background:#1f6feb}#circuit-panel button:disabled{opacity:.5;cursor:wait}
#circuit-panel .device{display:grid;grid-template-columns:90px 100px 1fr 120px 95px 65px;gap:8px;align-items:end;padding:8px 0;border-bottom:1px solid var(--edge)}
#circuit-panel .scroll{overflow:auto}#circuit-panel pre{white-space:pre-wrap;overflow-wrap:anywhere;max-height:300px;overflow:auto}
#circuit-panel svg{display:block;width:100%;height:auto;max-height:480px;background:#101820;border:1px solid var(--edge)}
#circuit-panel .muted{color:var(--dim)}#circuit-panel table{border-collapse:collapse;width:100%}#circuit-panel td,#circuit-panel th{text-align:left;padding:8px;border-bottom:1px solid var(--edge)}
#circuit-panel .bad{color:#ffaaa4}#circuit-panel .good{color:#8edca0}#circuit-panel :focus-visible{outline:2px solid var(--hi);outline-offset:2px}
@media(max-width:700px){#circuit-panel{padding:14px}#circuit-panel .device{grid-template-columns:1fr 1fr}#circuit-panel input{width:100%}}
</style>
<div class="bar"><h1 id="circuit-title">회로 편집 · ERC · ngspice</h1><button id="circuit-close" type="button" style="margin-left:auto">닫기</button></div>
<p class="muted">소자의 net 이름으로 연결합니다. 접지는 0, 값은 SI 단위입니다(1 kΩ = 1000, 1 µF = 1e-6). 범용 모델과 SKY130 모델을 선택할 수 있습니다.</p>
<p id="circuit-engine" role="status">시뮬레이터 확인 중…</p>
<div class="bar"><button id="circuit-save">설계 DB에 저장</button><button id="circuit-load">DB에서 불러오기</button><button id="circuit-import">JSON 가져오기</button><button id="circuit-export">JSON 저장</button><button id="circuit-spice">SPICE 내보내기</button><button id="circuit-example">분압기 예제</button><input id="circuit-file" type="file" accept=".json" hidden></div>
<p class="muted">DB 저장은 현재 서버의 CIRCUITS 라이브러리에 같은 이름의 회로를 대체합니다. 서버 재시작 후에도 보관하려면 JSON으로 저장하세요.</p>
<form id="circuit-form">
<button id="circuit-pdk-example" type="button">SKY130 인버터 예제</button>
<p>SKY130 선택 시 1.8 V NMOS/PMOS 공정 모델을 사용합니다. 공개 PDK 결과는 제조 승인과 별개입니다.</p>
<div class="bar"><label>모델<select id="circuit-profile"><option value="generic">범용 예제</option><option value="sky130">SKY130 · 1.8 V MOS</option></select></label><label>Corner<select id="circuit-corner"><option>tt</option><option>ff</option><option>ss</option><option>fs</option><option>sf</option></select></label></div>
<div class="bar"><label>회로 이름<input id="circuit-name" required maxlength="48"></label><label>온도 (°C)<input id="circuit-temp" type="number" min="-100" max="250" step="any" value="27"></label></div>
<div id="circuit-devices"></div><div class="bar"><button id="circuit-add" type="button">+ 소자 추가</button></div>
<details open><summary>연결도 · 같은 net 이름은 전기적으로 연결됩니다</summary><svg id="circuit-diagram" role="img" aria-label="회로 연결도"></svg></details>
<div class="bar"><label>해석<select id="circuit-analysis"><option value="op">동작점 (OP)</option><option value="dc">DC sweep</option><option value="ac">AC 주파수 응답</option><option value="tran">과도해석 (Transient)</option></select></label><div id="circuit-params" class="bar"></div></div>
<div class="bar"><button id="circuit-check" type="button">ERC / 넷리스트 확인</button><button id="circuit-run" type="submit" class="primary">시뮬레이션 실행</button></div>
</form>
<details><summary>Post-layout · 추출 회로 재시뮬레이션</summary><p>검증 창에서 LVS와 PEX가 통과한 실행 ID를 입력하세요. 위 회로에는 전원·입력 소스와 RLC 부하를 구성하고, 아래에 추출 핀과 testbench net의 연결을 지정합니다.</p>
<div class="bar"><label>검증 실행 ID<input id="circuit-layout-id" size="36"></label><label>핀 연결 JSON<input id="circuit-ports" size="60" value='{"VPB":"vdd","VNB":"0","VGND":"0","VPWR":"vdd","A":"vin","Y":"vout"}'></label><button id="circuit-postlayout">PEX 회로 실행</button></div></details>
<details><summary>실험 관리 · corners / 온도 / sweep / 합격 기준</summary>
<p class="muted">최대 30개 조합. 측정은 전체 샘플을 사용합니다. mean은 샘플 산술 평균입니다.</p>
<div class="bar"><label>Corners (쉼표 구분)<input id="circuit-corners" value="tt"></label><label>온도 °C (쉼표 구분)<input id="circuit-temperatures" value="27"></label><label>Sweep 소자 (선택)<input id="circuit-sweep-device" placeholder="V1"></label><label>Sweep 값 (SI, 쉼표 구분)<input id="circuit-sweep-values" placeholder="1.6,1.8"></label></div>
<div class="bar"><label>측정 신호<input id="circuit-measure-signal" value="v(vout)"></label><label>통계<select id="circuit-statistic"><option>last</option><option>min</option><option>max</option><option>mean</option></select></label><label>하한<input id="circuit-min" type="number" step="any" value="0.49"></label><label>상한<input id="circuit-max" type="number" step="any" value="0.51"></label></div>
<div class="bar"><button id="circuit-experiment">실험 실행</button><button id="circuit-experiment-export" disabled>실험 결과 JSON</button><button id="circuit-history">실행 이력</button></div>
<div class="scroll"><table><thead><tr><th>Corner / °C / sweep</th><th>측정값</th><th>판정</th><th>파형</th></tr></thead><tbody id="circuit-matrix"></tbody></table></div><pre id="circuit-history-result"></pre>
</details>
<p id="circuit-status" role="status" aria-live="polite">실행 전입니다. 회로 입력은 이 브라우저에 저장됩니다.</p>
<section id="circuit-results" hidden><h2>검사 · 해석 결과</h2><ul id="circuit-issues"></ul>
<div id="circuit-wave" hidden><div class="bar"><label>신호<select id="circuit-vector"></select></label><label>표시<select id="circuit-mode"><option value="real">실수값</option><option value="magnitude">크기</option><option value="phase">위상 (°)</option></select></label><button id="circuit-report">결과 JSON 저장</button></div><svg id="circuit-plot" role="img" aria-label="시뮬레이션 파형"></svg><p id="circuit-range" class="muted"></p><table><thead><tr><th>신호</th><th>마지막 값</th><th>단위</th></tr></thead><tbody id="circuit-values"></tbody></table></div>
<details><summary>SPICE 넷리스트</summary><pre id="circuit-netlist"></pre></details><details><summary>실행 로그</summary><pre id="circuit-log"></pre></details></section>`;
document.body.append(panel);
const $ = id => document.getElementById('circuit-' + id);
const key = 'mock-virtuoso.circuit.v1';
let circuit, defaults, result, available = false, busy = false;
const kinds = ['R','C','L','V','I','D','NMOS','PMOS'];
const ns = 'http://www.w3.org/2000/svg';
function svg(parent, kind, attrs, text) {
  const node = document.createElementNS(ns, kind);
  for (const [k,v] of Object.entries(attrs)) node.setAttribute(k,v);
  if (text !== undefined) node.textContent = text;
  parent.append(node); return node;
}
function download(data, filename, type='application/json') {
  const url=URL.createObjectURL(new Blob([typeof data==='string'?data:JSON.stringify(data,null,2)],{type}));
  const a=document.createElement('a'); a.href=url; a.download=filename; a.click(); setTimeout(()=>URL.revokeObjectURL(url),1000);
}
async function api(path, data) {
  const response=await fetch('/api/circuit/'+path, data===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
  const value=await response.json(); if(!response.ok) throw Error(value.error||'요청 실패'); return value;
}
function say(message) { $('status').textContent=message; }
function remember() { try {localStorage.setItem(key,JSON.stringify(circuit));} catch {say('브라우저 저장 실패: JSON으로 내보내세요.');} }
function changed() { remember(); $('results').hidden=true; result=null; diagram(); }
function field(row, label, value, change, numeric=false) {
  const wrap=document.createElement('label'); wrap.textContent=label;
  const input=document.createElement('input'); input.value=value; input.required=true;
  if(numeric){input.type='number';input.step='any';}
  input.oninput=()=>{change(numeric?Number(input.value):input.value);changed();}; wrap.append(input); row.append(wrap); return input;
}
function devices() {
  $('devices').replaceChildren();
  circuit.devices.forEach((d,i)=>{
    const row=document.createElement('div');row.className='device';row.dataset.index=i;
    field(row,'이름',d.id,v=>d.id=v);
    const label=document.createElement('label');label.textContent='소자';const select=document.createElement('select');
    for(const k of kinds){const o=document.createElement('option');o.value=k;o.textContent=k;select.append(o);}select.value=d.kind;
    select.onchange=()=>{const k=select.value;circuit.devices[i]=newDevice(k,d.id);devices();changed();};label.append(select);row.append(label);
    field(row,d.kind.endsWith('MOS')?'net (D, G, S, B)':'net (+, −)',d.nodes.join(', '),v=>d.nodes=v.split(',').map(x=>x.trim()));
    if(d.kind.endsWith('MOS')) {field(row,'폭 W (m)',d.width,v=>d.width=v,true);field(row,'길이 L (m)',d.length,v=>d.length=v,true);}
    else {
      if(d.kind!=='D') field(row,({R:'저항 (Ω)',C:'용량 (F)',L:'인덕턴스 (H)',V:'전압 (V)',I:'전류 (A)'})[d.kind],d.value,v=>d.value=v,true);
      else row.append(document.createElement('span'));
      if(['V','I'].includes(d.kind)) field(row,'AC 크기',d.ac||0,v=>d.ac=v,true);else row.append(document.createElement('span'));
    }
    const del=document.createElement('button');del.type='button';del.textContent='삭제';del.onclick=()=>{circuit.devices.splice(i,1);devices();changed();};row.append(del);$('devices').append(row);
    if(d.pulse){const note=document.createElement('p');note.textContent=d.id+' PULSE: '+JSON.stringify(d.pulse)+' (JSON에서 편집)';$('devices').append(note);}
  });
}
function newDevice(kind,id) {
  const d={id,kind,nodes:kind.endsWith('MOS')?['out','in','0','0']:['out','0']};
  if(kind.endsWith('MOS')) Object.assign(d,{width:1e-6,length:1e-6});
  else if(kind!=='D') d.value=({R:1000,C:1e-6,L:1e-3,V:1,I:1e-3})[kind];
  if(['V','I'].includes(kind)) d.ac=0;return d;
}
function analysis() {
  $('params').replaceChildren(); const a=circuit.analysis;
  for(const name of Object.keys(a).filter(k=>k!=='type')) field($('params'),({source:'Sweep 소자',start:'시작',stop:'종료',step:'간격',points:'점/decade'})[name],a[name],v=>a[name]=v,name!=='source');
}
function apply(value) {circuit=structuredClone(value);$('profile').value=circuit.model_profile||'generic';$('corner').value=circuit.corner||'tt';$('name').value=circuit.name;$('temp').value=circuit.temperature_c;$('analysis').value=circuit.analysis.type;devices();analysis();changed();}
function diagram() {
  const target=$('diagram');target.replaceChildren();const columns=3,rows=Math.max(1,Math.ceil(circuit.devices.length/columns));target.setAttribute('viewBox',`0 0 900 ${rows*125}`);
  circuit.devices.forEach((d,i)=>{
    const x=150+(i%columns)*300,y=55+Math.floor(i/columns)*125;
    svg(target,'path',{d:`M ${x-105} ${y} H ${x-42} M ${x+42} ${y} H ${x+105}`,stroke:'#8abfff',fill:'none'});
    svg(target,'rect',{x:x-42,y:y-20,width:84,height:40,rx:5,fill:'#1f3048',stroke:'#8abfff'});
    svg(target,'text',{x,y:y+5,fill:'#e6edf3','text-anchor':'middle','font-size':14},d.kind+' '+d.id);
    svg(target,'text',{x:x-105,y:y-10,fill:'#aac5e5','font-size':12},d.nodes[0]||'?');
    svg(target,'text',{x:x+105,y:y-10,fill:'#aac5e5','text-anchor':'end','font-size':12},d.nodes[1]||'?');
    svg(target,'text',{x,y:y+43,fill:'#8b949e','text-anchor':'middle','font-size':12},d.kind.endsWith('MOS')?'D,G,S,B: '+d.nodes.join(', '):(d.value??'generic diode'));
  });
}
function render(report) {
  result=report;$('results').hidden=false;$('netlist').textContent=report.netlist||'';$('log').textContent=report.log||report.reason||'';
  $('issues').replaceChildren();
  const issues=report.erc.issues;
  for(const issue of issues.length?issues:[{message:report.erc.status==='not_run'?'Post-layout: 추출된 회로 연결 사용, 구조적 ERC 별도 미실행':'구조적 ERC 통과 (공정 sign-off ERC 아님)'}]) {
    const li=document.createElement('li');li.className=issues.length?'bad':'good';li.textContent=[issue.code,issue.device||issue.net,issue.message].filter(Boolean).join(' · ');$('issues').append(li);
  }
  $('wave').hidden=!report.data;
  if(report.data){
    $('vector').replaceChildren();$('values').replaceChildren();
    report.data.columns.forEach((column,index)=>{
      const option=document.createElement('option');option.value=index;option.textContent=column.name;$('vector').append(option);
      const row=document.createElement('tr');const last=column.real.length-1;
      for(const text of [column.name,column.real[last].toPrecision(6)+(report.data.complex?` + j${column.imag[last].toPrecision(6)}`:''),column.unit]){const td=document.createElement('td');td.textContent=text;row.append(td);}$('values').append(row);
    });
    $('vector').value=String(Math.max(0,report.data.columns.findIndex(c=>c.name==='v(vout)')));
    $('mode').value=report.data.complex?'magnitude':'real';plot();
  }
}
function plot() {
  if(!result?.data)return;
  const data=result.data,column=data.columns[Number($('vector').value)],mode=$('mode').value;
  const values=column.real.map((r,i)=>mode==='phase'?Math.atan2(column.imag[i],r)*180/Math.PI:mode==='magnitude'?Math.hypot(r,column.imag[i]):r);
  const analysisType=result.analysis?.type||circuit.analysis.type;
  const op=analysisType==='op';const xs=op?values.map((_,i)=>i):data.columns[0].real;
  const axis=xs.map(x=>analysisType==='ac'?Math.log10(x):x);
  const xmin=Math.min(...axis),xmax=Math.max(...axis),ymin=Math.min(...values),ymax=Math.max(...values);
  const target=$('plot');target.replaceChildren();target.setAttribute('viewBox','0 0 900 300');
  svg(target,'path',{d:'M 75 20 V 260 H 870',fill:'none',stroke:'#52677e'});
  const coords=values.map((y,i)=>[75+(axis[i]-xmin)/(xmax-xmin||1)*795,260-(y-ymin)/(ymax-ymin||1)*230]);
  svg(target,'polyline',{points:coords.map(x=>x.join(',')).join(' '),fill:'none',stroke:'#69b7ff','stroke-width':2});
  if(coords.length===1)svg(target,'circle',{cx:coords[0][0],cy:coords[0][1],r:4,fill:'#69b7ff'});
  for(const [x,y,t] of [[5,25,ymax.toPrecision(4)],[5,260,ymin.toPrecision(4)],[75,285,String(xs[0])],[790,285,String(xs.at(-1))]]) svg(target,'text',{x,y,fill:'#b8c8d8','font-size':12},t);
  $('range').textContent=`${column.name} · ${mode==='phase'?'degrees':column.unit} · ${data.sample_count} samples (${data.returned_samples} 표시) · X: ${op?'동작점':data.columns[0].name}${analysisType==='ac'?' / log10':''}`;
}
button.onclick=()=>panel.showModal();$('close').onclick=()=>panel.close();
$('profile').onchange=()=>{circuit.model_profile=$('profile').value;changed();};
$('pdk-example').onclick=()=>{
  apply({name:'SKY130_INV',model_profile:'sky130',corner:'tt',temperature_c:27,devices:[
    {id:'VDD',kind:'V',nodes:['vdd','0'],value:1.8,ac:0},
    {id:'V1',kind:'V',nodes:['vin','0'],value:0,ac:0},
    {id:'MN',kind:'NMOS',nodes:['vout','vin','0','0'],width:.65e-6,length:.15e-6},
    {id:'MP',kind:'PMOS',nodes:['vout','vin','vdd','vdd'],width:1e-6,length:.15e-6}],
    analysis:{type:'dc',source:'V1',start:0,stop:1.8,step:.02}});
  $('corners').value='tt,ff,ss';$('temperatures').value='27';$('sweep-device').value='';$('sweep-values').value='';$('measure-signal').value='v(vout)';$('min').value='-0.01';$('max').value='0.01';$('statistic').value='last';
};
$('corner').onchange=()=>{circuit.corner=$('corner').value;changed();};
let experimentResult;
$('postlayout').onclick=async()=>{
  if(busy)return;busy=true;const controls=Array.from(panel.querySelectorAll('input,select,button')).filter(n=>n.id!=='circuit-close');controls.forEach(n=>n.disabled=true);
  try{say('추출 회로를 ngspice로 해석 중…');const report=await api('postlayout',{run_id:$('layout-id').value.trim(),circuit:structuredClone(circuit),ports:JSON.parse($('ports').value)});render(report);say('Post-layout '+report.status+(report.reason?' · '+report.reason:''));}catch(e){say(e.message);}finally{busy=false;controls.forEach(n=>n.disabled=false);$('run').disabled=!available;}
};
$('experiment-export').onclick=()=>{if(experimentResult)download(experimentResult,'experiment-result.json');};
$('history').onclick=async()=>{try{const response=await api('history');$('history-result').textContent=JSON.stringify(response,null,2);}catch(e){say(e.message);}};
$('experiment').onclick=async()=>{
  if(busy)return;busy=true;
  const controls=Array.from(panel.querySelectorAll('input,select,button')).filter(n=>n.id!=='circuit-close');controls.forEach(n=>n.disabled=true);
  const snapshot=structuredClone(circuit);
  try{
    const measurement={name:'acceptance',signal:$('measure-signal').value,statistic:$('statistic').value};
    for(const bound of ['min','max'])if($(bound).value!=='')measurement[bound]=Number($(bound).value);
    const plan={name:snapshot.name,circuit:snapshot,corners:$('corners').value.split(',').map(v=>v.trim()),temperatures:$('temperatures').value.split(',').map(Number),measurements:[measurement]};
    if($('sweep-device').value.trim())plan.sweep={device:$('sweep-device').value.trim(),values:$('sweep-values').value.split(',').map(Number)};
    say('실험 실행 중… 각 조합의 원본 데이터와 판정을 저장합니다.');
    experimentResult=await api('experiment',plan);$('matrix').replaceChildren();
    for(const run of experimentResult.runs){
      const row=document.createElement('tr');
      for(const text of [`${run.corner} / ${run.temperature_c} / ${run.sweep_value??'—'}`,run.measurements.map(m=>m.value??m.reason).join(', ')||run.simulation.reason||'실행 실패',run.status]){const cell=document.createElement('td');cell.textContent=text;row.append(cell);}
      const cell=document.createElement('td'),view=document.createElement('button');view.textContent='보기';view.onclick=()=>render(run.simulation);cell.append(view);row.append(cell);$('matrix').append(row);
    }
    say(`실험 ${experimentResult.status} · ${experimentResult.runs.length}개 조합`);
  }catch(e){say(e.message);}finally{busy=false;controls.forEach(n=>n.disabled=false);$('run').disabled=!available;$('experiment-export').disabled=!experimentResult;}
};
$('name').oninput=()=>{circuit.name=$('name').value;changed();};$('temp').oninput=()=>{circuit.temperature_c=Number($('temp').value);changed();};
$('analysis').onchange=()=>{const k=$('analysis').value;circuit.analysis=({op:{type:k},dc:{type:k,source:'V1',start:0,stop:2,step:0.1},ac:{type:k,start:1,stop:1e6,points:50},tran:{type:k,step:1e-5,stop:0.01}})[k];analysis();changed();};
$('add').onclick=()=>{if(circuit.devices.length>=128){say('소자는 최대 128개입니다.');return;}let n=1;while(circuit.devices.some(d=>d.id.toLowerCase()==='r'+n))n++;circuit.devices.push(newDevice('R','R'+n));devices();changed();};
$('example').onclick=()=>{if(defaults)apply(defaults);};
$('save').onclick=async()=>{try{await api('save',circuit);say('CIRCUITS/'+circuit.name+'/schematic에 저장했습니다.');}catch(e){say(e.message);}};
$('load').onclick=async()=>{try{const loaded=await api('load',{name:$('name').value});apply(loaded.circuit);say('설계 DB의 회로를 불러왔습니다.');}catch(e){say(e.message);}};
$('import').onclick=()=>$('file').click();$('file').onchange=async()=>{try{const file=$('file').files[0];if(!file)return;if(file.size>256*1024)throw Error('JSON 최대 크기는 256 KiB입니다.');const checked=await api('check',JSON.parse(await file.text()));apply(checked.circuit);render(checked);say('회로를 불러왔습니다.');}catch(e){say(e.message);}finally{$('file').value='';}};
$('export').onclick=async()=>{try{const checked=await api('check',circuit);download(checked.circuit,'circuit.json');}catch(e){say(e.message);}};
$('spice').onclick=async()=>{try{const checked=await api('check',circuit);download(checked.netlist,circuit.name+'.cir','text/plain');}catch(e){say(e.message);}};
$('check').onclick=async()=>{try{const checked=await api('check',circuit);render(checked);say('ERC: '+checked.erc.status);}catch(e){say(e.message);}};
$('form').onsubmit=async event=>{
  event.preventDefault();if(busy)return;busy=true;
  const controls=Array.from(panel.querySelectorAll('input,select,button')).filter(n=>n.id!=='circuit-close');controls.forEach(n=>n.disabled=true);
  const snapshot=structuredClone(circuit);say('ngspice 실행 중…');$('results').hidden=true;
  try{const report=await api('simulate',snapshot);render(report);say(report.status==='pass'?`해석 완료 · ${report.elapsed_s}s`:report.reason||report.status);}catch(e){say(e.message);}finally{busy=false;controls.forEach(n=>n.disabled=false);$('run').disabled=!available;}
};
$('vector').onchange=plot;$('mode').onchange=plot;$('report').onclick=()=>download(result,'simulation-result.json');
const initialControls=Array.from(panel.querySelectorAll('input,select,button')).filter(n=>n.id!=='circuit-close');initialControls.forEach(n=>n.disabled=true);
(async()=>{try{const data=await api('catalog');defaults=data.example;available=data.available;$('engine').textContent=available?'ngspice 준비됨 · OP / DC / AC / Transient':'ngspice 미설치 · ERC와 SPICE 내보내기는 사용 가능합니다.';let saved;try{saved=JSON.parse(localStorage.getItem(key)||'null');}catch{};if(saved){try{apply((await api('check',saved)).circuit);}catch{apply(defaults);}}else apply(defaults);initialControls.forEach(n=>n.disabled=false);$('run').disabled=!available;}catch(e){say(e.message);$('run').disabled=true;}})();
})();
