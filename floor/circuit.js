// Runnable educational CMOS topologies; these are not foundry library cell views.
function standardCellExamples() {
  const definitions=[['INV',['A'],'!A'],['BUF',['A'],'A'],['NAND2',['A','B'],'!(A & B)'],
    ['NOR2',['A','B'],'!(A | B)'],['AND2',['A','B'],'A & B'],['OR2',['A','B'],'A | B'],
    ['XOR2',['A','B'],'A ^ B'],['XNOR2',['A','B'],'!(A ^ B)'],
    ['MUX2',['A','B','S'],'S ? B : A'],['AOI21',['A','B','C'],'!((A & B) | C)'],
    ['OAI21',['A','B','C'],'!((A | B) & C)']];
  return definitions.map(([name,inputs,expression])=>{
    const devices=[{id:'VDD',kind:'V',nodes:['vdd','0'],value:1.8,ac:0}];
    let serial=0;
    const internal=()=>`n${++serial}`;
    function mos(kind,d,g,s,w){devices.push({id:`M${++serial}`,kind,nodes:[d,g,s,kind==='NMOS'?'0':'vdd'],width:w*1e-6,length:.15e-6});}
    function inv(a,y){mos('NMOS',y,a,'0',.65);mos('PMOS',y,a,'vdd',1.3);}
    function nand(a,b,y){const n=internal();mos('NMOS',y,a,n,1.3);mos('NMOS',n,b,'0',1.3);mos('PMOS',y,a,'vdd',1.3);mos('PMOS',y,b,'vdd',1.3);}
    function nor(a,b,y){const n=internal();mos('NMOS',y,a,'0',.65);mos('NMOS',y,b,'0',.65);mos('PMOS',y,a,n,2.6);mos('PMOS',n,b,'vdd',2.6);}
    function and(a,b,y){const n=internal();nand(a,b,n);inv(n,y);}
    function or(a,b,y){const n=internal();nor(a,b,n);inv(n,y);}
    function xor(a,b,y){const n=internal(),p=internal(),q=internal();nand(a,b,n);nand(a,n,p);nand(b,n,q);nand(p,q,y);}
    const y='vout';
    if(name==='INV')inv('a',y);
    if(name==='BUF'){const n=internal();inv('a',n);inv(n,y);}
    if(name==='NAND2')nand('a','b',y);
    if(name==='NOR2')nor('a','b',y);
    if(name==='AND2')and('a','b',y);
    if(name==='OR2')or('a','b',y);
    if(name==='XOR2')xor('a','b',y);
    if(name==='XNOR2'){const n=internal();xor('a','b',n);inv(n,y);}
    if(name==='MUX2'){const ns=internal(),p=internal(),q=internal();inv('s',ns);nand('a',ns,p);nand('b','s',q);nand(p,q,y);}
    if(name==='AOI21'){const n=internal();and('a','b',n);nor(n,'c',y);}
    if(name==='OAI21'){const n=internal();or('a','b',n);nand(n,'c',y);}
    inputs.forEach((input,i)=>{const half=20e-9*2**i;devices.push({id:'V'+input,kind:'V',nodes:[input.toLowerCase(),'0'],value:0,ac:0,
      pulse:{low:0,high:1.8,delay:half,rise:.1e-9,fall:.1e-9,width:half-.1e-9,period:2*half}});});
    devices.push({id:'CL',kind:'C',nodes:[y,'0'],value:5e-15});
    return {name,inputs,expression,circuit:{name:'SKY130_'+name,model_profile:'sky130',corner:'tt',temperature_c:27,devices,
      analysis:{type:'tran',step:.1e-9,stop:20e-9*2**inputs.length}}};
  });
}

// Circuit editor.
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

#circuit-panel{padding:24px;background:var(--bg)}
#circuit-panel .circuit-heading{position:sticky;top:-24px;z-index:2;margin-top:0;background:var(--bg);padding:14px 0;border-bottom:1px solid var(--edge)}
#circuit-panel fieldset{min-width:0;border:1px solid var(--edge);border-radius:12px;background:var(--surface);padding:20px;margin:20px 0}
#circuit-panel legend{font-size:15px;font-weight:650;color:var(--hi);padding:0 8px}
#circuit-panel input,#circuit-panel select{background:var(--input);color:var(--ink);border-color:var(--border);min-height:40px}
#circuit-panel button{background:var(--surface);border-color:var(--border);border-radius:7px;padding:9px 12px;font-weight:500}
#circuit-panel button:hover:not(:disabled){background:var(--hover);border-color:var(--hi)}
#circuit-panel button.primary{background:var(--accent);color:var(--accent-ink);border-color:var(--accent)}
#circuit-panel .device{gap:12px;padding:14px 0}#circuit-panel label{font-size:12px;color:var(--dim)}
#circuit-panel label input,#circuit-panel label select{font-size:14px}
#circuit-panel details{border:1px solid var(--edge);border-radius:10px;background:var(--surface);padding:14px 16px;margin:12px 0}
#circuit-panel summary{cursor:pointer;font-weight:600;color:var(--ink)}
#circuit-panel details[open]>summary{margin-bottom:12px}
#circuit-panel #circuit-status,#circuit-panel #circuit-engine{padding:11px 14px;border:1px solid var(--edge);border-radius:8px;background:var(--hover);color:var(--ink)}
#circuit-panel svg{background:var(--diagram);border-radius:8px}
#circuit-panel .bad{color:var(--err)}#circuit-panel .good{color:var(--ok)}
#circuit-panel th{background:var(--input);font-size:12px;color:var(--dim)}
#circuit-panel pre{background:var(--input);padding:12px;border-radius:8px}
#circuit-panel .theme-control{flex-direction:row;align-items:center;margin-left:auto}
#circuit-panel .inline-choice{flex-direction:row;align-items:center;gap:7px;border:1px solid var(--edge);border-radius:7px;padding:6px 9px;background:var(--input)}
#circuit-panel input[type=checkbox]{width:17px;min-height:17px;accent-color:var(--accent)}
#circuit-panel input[type=range]{padding:0;min-height:24px;accent-color:var(--accent)}
#circuit-panel .wave-scroll{overflow-x:auto}#circuit-panel #circuit-plot{min-width:640px;max-height:none;cursor:crosshair}
#circuit-panel #circuit-probe{display:block;font:600 13px/1.8 ui-monospace,Consolas,monospace;padding:10px;background:var(--hover);border-radius:7px;overflow-wrap:anywhere}
#circuit-panel .trace-swatch{width:10px;height:10px;border-radius:50%;display:inline-block}
@media(max-width:700px){#circuit-panel{padding:14px}#circuit-panel .circuit-heading{top:-14px}#circuit-panel .circuit-heading h1{font-size:18px;flex-basis:100%}#circuit-panel fieldset{padding:12px}#circuit-panel .device{grid-template-columns:minmax(0,1fr) minmax(0,1fr)}#circuit-panel .theme-control{margin-left:0}#circuit-panel .theme-control select{width:auto}}

</style>
<div class="bar circuit-heading"><h1 id="circuit-title">회로 편집 · ERC · ngspice</h1><button id="circuit-close" type="button" style="margin-left:auto">닫기</button></div>
<p class="muted">소자의 net 이름으로 연결합니다. 접지는 0, 값은 SI 단위입니다(1 kΩ = 1000, 1 µF = 1e-6). 범용 모델과 SKY130 모델을 선택할 수 있습니다.</p>
<p id="circuit-engine" role="status">시뮬레이터 확인 중…</p>
<div class="bar"><button id="circuit-save">설계 DB에 저장</button><button id="circuit-load">DB에서 불러오기</button><button id="circuit-import">JSON 가져오기</button><button id="circuit-export">JSON 저장</button><button id="circuit-spice">SPICE 내보내기</button><button id="circuit-example">분압기 예제</button><input id="circuit-file" type="file" accept=".json" hidden></div>
<p class="muted">DB 저장은 현재 서버의 CIRCUITS 라이브러리에 같은 이름의 회로를 대체합니다. 서버 재시작 후에도 보관하려면 JSON으로 저장하세요.</p>
<form id="circuit-form"><fieldset><legend>1. 회로와 공정 모델</legend>
<div class="bar"><label>표준 셀 예제<select id="circuit-cell-example"></select></label><button id="circuit-cell-load" type="button">예제 불러오기</button></div>
<p id="circuit-cell-description" class="muted"></p>
<p class="muted">학습용 CMOS 회로입니다. 공인 표준 셀 라이브러리의 레이아웃·타이밍 뷰는 포함하지 않습니다. 1.8 V 입력과 5 fF 부하로 모든 입력 조합을 순서대로 실행합니다.</p>
<button id="circuit-pdk-example" type="button">SKY130 인버터 예제</button>
<p>SKY130 선택 시 1.8 V NMOS/PMOS 공정 모델을 사용합니다. 공개 PDK 결과는 제조 승인과 별개입니다.</p>
<div class="bar"><label>모델<select id="circuit-profile"><option value="generic">범용 예제</option><option value="sky130">SKY130 · 1.8 V MOS</option></select></label><label>Corner<select id="circuit-corner"><option>tt</option><option>ff</option><option>ss</option><option>fs</option><option>sf</option></select></label></div>
<div class="bar"><label>회로 이름<input id="circuit-name" required maxlength="48"></label><label>온도 (°C)<input id="circuit-temp" type="number" min="-100" max="250" step="any" value="27"></label></div>
</fieldset><fieldset><legend>2. 소자와 연결</legend><div id="circuit-devices"></div><div class="bar"><button id="circuit-add" type="button">+ 소자 추가</button></div>
<details open><summary>연결도 · 같은 net 이름은 전기적으로 연결됩니다</summary><svg id="circuit-diagram" role="img" aria-label="회로 연결도"></svg></details>
</fieldset><fieldset><legend>3. 해석과 실행</legend><div class="bar"><label>해석<select id="circuit-analysis"><option value="op">동작점 (OP)</option><option value="dc">DC sweep</option><option value="ac">AC 주파수 응답</option><option value="tran">과도해석 (Transient)</option></select></label><div id="circuit-params" class="bar"></div></div>
<div class="bar"><button id="circuit-check" type="button">ERC / 넷리스트 확인</button><button id="circuit-run" type="submit" class="primary">시뮬레이션 실행</button></div>
</fieldset></form>
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
<div id="circuit-wave" hidden><div class="bar"><label>신호<select id="circuit-vector"></select></label><label>표시<select id="circuit-mode"><option value="real">실수값</option><option value="magnitude">크기</option><option value="phase">위상 (°)</option></select></label><label class="inline-choice"><input id="circuit-multi" type="checkbox">여러 신호 함께</label><button id="circuit-report">결과 JSON 저장</button></div>
<div id="circuit-traces" class="bar" aria-label="표시할 신호"></div>
<div class="bar"><button id="circuit-zoom-in" type="button">확대 +</button><button id="circuit-zoom-out" type="button">축소 −</button><button id="circuit-zoom-reset" type="button">전체 보기</button><label>시간축 이동<input id="circuit-pan" type="range" min="0" max="100" value="0" step="1"></label></div>
<div class="wave-scroll"><svg id="circuit-plot" role="img" aria-label="시뮬레이션 파형"></svg></div>
<label>측정 커서<input id="circuit-cursor" type="range" min="0" max="0" value="0" step="1"></label><output id="circuit-probe" data-no-translate></output>
<p id="circuit-range" class="muted"></p><details><summary>신호별 마지막 값</summary><table><thead><tr><th>신호</th><th>마지막 값</th><th>단위</th></tr></thead><tbody id="circuit-values" data-no-translate></tbody></table></details></div>
<details><summary>SPICE 넷리스트</summary><pre id="circuit-netlist"></pre></details><details><summary>실행 로그</summary><pre id="circuit-log"></pre></details></section>`;
document.body.append(panel);
const $ = id => document.getElementById('circuit-' + id);
const key = 'mock-virtuoso.circuit.v1';
let circuit, defaults, result, available = false, busy = false;
const kinds = ['R','C','L','V','I','D','NMOS','PMOS'];
const cellExamples=standardCellExamples();
for(const example of cellExamples){const option=document.createElement('option');option.value=example.name;option.textContent=example.name+' · '+example.expression;$('cell-example').append(option);}
function describeExample(){const ex=cellExamples.find(e=>e.name===$('cell-example').value);$('cell-description').textContent=`${ex.name} · Y = ${ex.expression} · ${ex.inputs.join(', ')} → vout · 1.8 V / 5 fF`;}
$('cell-example').onchange=describeExample;describeExample();
$('cell-load').onclick=()=>{const ex=cellExamples.find(e=>e.name===$('cell-example').value);apply(ex.circuit);$('multi').checked=true;$('corners').value='tt';$('temperatures').value='27';$('sweep-device').value='';$('sweep-values').value='';$('measure-signal').value='v(vout)';$('statistic').value='max';$('min').value='1.6';$('max').value='1.9';say('표준 셀 예제를 불러왔습니다. 시뮬레이션 실행 후 입력과 vout 파형을 비교하세요.');};
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
    svg(target,'path',{d:`M ${x-105} ${y} H ${x-42} M ${x+42} ${y} H ${x+105}`,stroke:'var(--plot)',fill:'none'});
    svg(target,'rect',{x:x-42,y:y-20,width:84,height:40,rx:5,fill:'var(--node)',stroke:'var(--plot)'});
    svg(target,'text',{x,y:y+5,fill:'var(--ink)','text-anchor':'middle','font-size':14},d.kind+' '+d.id);
    svg(target,'text',{x:x-105,y:y-10,fill:'var(--dim)','font-size':12},d.nodes[0]||'?');
    svg(target,'text',{x:x+105,y:y-10,fill:'var(--dim)','text-anchor':'end','font-size':12},d.nodes[1]||'?');
    svg(target,'text',{x,y:y+43,fill:'var(--dim)','text-anchor':'middle','font-size':12},d.kind.endsWith('MOS')?'D,G,S,B: '+d.nodes.join(', '):(d.value??'generic diode'));
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
    waveZoom=1;$('pan').value=0;$('traces').replaceChildren();
    const preferred=['v(a)','v(b)','v(c)','v(s)','v(clk)','v(d)','v(vin)','v(in)','v(out)','v(vout)','v(q)'];
    report.data.columns.map((column,index)=>({column,index})).filter(({column})=>preferred.includes(column.name.toLowerCase()))
      .sort((a,b)=>preferred.indexOf(a.column.name.toLowerCase())-preferred.indexOf(b.column.name.toLowerCase())).forEach(({column,index})=>{
      const label=document.createElement('label');label.className='inline-choice';label.dataset.noTranslate='';
      const input=document.createElement('input');input.type='checkbox';input.checked=true;input.value=index;input.onchange=plot;
      const swatch=document.createElement('span');swatch.className='trace-swatch';swatch.style.background=traceColors[index%traceColors.length];
      label.append(input,swatch,document.createTextNode(column.name));$('traces').append(label);
    });
    $('vector').replaceChildren();$('values').replaceChildren();
    report.data.columns.forEach((column,index)=>{
      const option=document.createElement('option');option.value=index;option.textContent=column.name;$('vector').append(option);
      const row=document.createElement('tr');const last=column.real.length-1;
      for(const text of [column.name,column.real[last].toPrecision(6)+(report.data.complex?` + j${column.imag[last].toPrecision(6)}`:''),column.unit]){const td=document.createElement('td');td.textContent=text;row.append(td);}$('values').append(row);
    });
    $('vector').value=String(Math.max(0,report.data.columns.findIndex(c=>c.name==='v(vout)')));
    $('mode').value=report.data.complex?'magnitude':'real';plot();
    $('wave').scrollIntoView({block:'start'});
  }
}
const traceColors=['#2563eb','#d97706','#0891b2','#9333ea','#dc2626','#059669'];
let waveZoom=1, waveCursor=null;
function engineering(value,unit=''){
  if(!Number.isFinite(value))return '—';
  const abs=Math.abs(value);
  const prefixes=[[1e9,'G'],[1e6,'M'],[1e3,'k'],[1,''],[1e-3,'m'],[1e-6,'µ'],[1e-9,'n'],[1e-12,'p'],[1e-15,'f']];
  const [scale,prefix]=abs===0?[1,'']:prefixes.find(([n])=>abs>=n)||[1e-15,'f'];
  return Number((value/scale).toPrecision(4))+' '+prefix+unit;
}
function plot() {
  if(!result?.data)return;
  const data=result.data,mode=$('mode').value,analysisType=result.analysis?.type||circuit.analysis.type;
  const op=analysisType==='op',xs=op?data.columns[0].real.map((_,i)=>i):data.columns[0].real;
  const axis=xs.map(x=>analysisType==='ac'?Math.log10(x):x),total=axis.length;
  let selected=$('multi').checked?Array.from($('traces').querySelectorAll('input:checked')).map(input=>Number(input.value)):[];
  if(!selected.length)selected=[Number($('vector').value)];
  $('traces').hidden=!$('multi').checked;
  const fullMin=axis[0],fullMax=axis.at(-1),span=(fullMax-fullMin)/waveZoom;
  const xmin=fullMin+(fullMax-fullMin-span)*Number($('pan').value)/100,xmax=xmin+span;
  const visible=axis.map((x,i)=>i).filter(i=>axis[i]>=xmin&&axis[i]<=xmax);
  const first=visible[0]??0,last=visible.at(-1)??total-1;
  $('pan').disabled=waveZoom===1||op;$('zoom-in').disabled=op||waveZoom>=32;$('zoom-out').disabled=op||waveZoom===1;
  const target=$('plot');target.replaceChildren();const height=selected.length*150+44;
  target.setAttribute('viewBox',`0 0 960 ${height}`);
  const xcoord=x=>100+(x-xmin)/(xmax-xmin||1)*825;
  const xUnit=analysisType==='tran'?'s':analysisType==='ac'?'Hz':data.columns[0].unit==='current'?'A':'V';
  for(let tick=0;tick<=5;tick++){
    const x=100+825*tick/5,scaled=xmin+(xmax-xmin)*tick/5,value=analysisType==='ac'?10**scaled:scaled;
    svg(target,'line',{x1:x,x2:x,y1:12,y2:height-36,stroke:'var(--edge)','stroke-dasharray':'3 5'});
    svg(target,'text',{x,y:height-12,fill:'var(--dim)','text-anchor':'middle','font-size':12},op?'OP':engineering(value,xUnit));
  }
  const traces=[];
  selected.forEach((index,lane)=>{
    const column=data.columns[index];
    const values=column.real.map((r,i)=>mode==='phase'?Math.atan2(column.imag[i],r)*180/Math.PI:mode==='magnitude'?Math.hypot(r,column.imag[i]):r);
    const shown=visible.map(i=>values[i]);
    let ymin=Math.min(...shown),ymax=Math.max(...shown);if(!shown.length){ymin=0;ymax=1;}
    const pad=(ymax-ymin)*.08||Math.max(Math.abs(ymax)*.05,.05);ymin-=pad;ymax+=pad;
    const top=lane*150+35,bottom=lane*150+132,color=traceColors[index%traceColors.length];
    const unit=mode==='phase'?'°':column.unit==='voltage'?'V':column.unit==='current'?'A':column.unit;
    svg(target,'text',{x:100,y:lane*150+20,fill:'var(--ink)','font-size':14,'font-weight':600},column.name);
    for(const fraction of [0,.5,1]){
      const y=bottom-fraction*(bottom-top),v=ymin+fraction*(ymax-ymin);
      svg(target,'line',{x1:100,x2:925,y1:y,y2:y,stroke:'var(--edge)'});
      svg(target,'text',{x:88,y:y+4,fill:'var(--dim)','text-anchor':'end','font-size':12},engineering(v,unit));
    }
    const coords=visible.map(i=>[xcoord(axis[i]),bottom-(values[i]-ymin)/(ymax-ymin)*(bottom-top)]);
    svg(target,'polyline',{points:coords.map(p=>p.join(',')).join(' '),fill:'none',stroke:color,'stroke-width':2,'data-trace':column.name});
    if(coords.length===1)svg(target,'circle',{cx:coords[0][0],cy:coords[0][1],r:4,fill:color});
    traces.push({column,values,unit});
  });
  const cursor=svg(target,'line',{x1:100,x2:100,y1:12,y2:height-36,stroke:'var(--ink)','stroke-width':1,'stroke-dasharray':'5 4'});
  const probe=$('cursor');probe.min=first;probe.max=last;probe.value=Math.min(last,Math.max(first,Number(probe.value)));
  function inspect(index){
    probe.value=index;const x=xcoord(axis[index]);cursor.setAttribute('x1',x);cursor.setAttribute('x2',x);
    $('probe').textContent=(op?'OP':engineering(xs[index],xUnit))+' · '+traces.map(t=>t.column.name+' = '+engineering(t.values[index],t.unit)).join(' · ');
  }
  waveCursor=inspect;inspect(Number(probe.value));
  target.onpointermove=event=>{
    const bounds=target.getBoundingClientRect(),x=(event.clientX-bounds.left)/bounds.width*960;
    const value=xmin+Math.min(1,Math.max(0,(x-100)/825))*(xmax-xmin);
    let nearest=first;for(const index of visible)if(Math.abs(axis[index]-value)<Math.abs(axis[nearest]-value))nearest=index;
    inspect(nearest);
  };
  $('range').textContent=`${data.sample_count} samples · ${data.returned_samples} displayed · ${selected.length} traces · ${waveZoom}× · X: ${op?'OP':data.columns[0].name}${analysisType==='ac'?' / log10':''}`;
}
$('multi').onchange=plot;$('pan').oninput=plot;$('cursor').oninput=()=>waveCursor?.(Number($('cursor').value));
$('zoom-in').onclick=()=>{waveZoom=Math.min(32,waveZoom*2);plot();};
$('zoom-out').onclick=()=>{waveZoom=Math.max(1,waveZoom/2);plot();};
$('zoom-reset').onclick=()=>{waveZoom=1;$('pan').value=0;plot();};
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
