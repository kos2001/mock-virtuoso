(() => {
'use strict';
const $ = id => document.getElementById('verify-' + id);
const storageKey = 'mock-virtuoso.verification.v1';
const labels = {pass:'통과', fail:'위반 / 불일치', error:'실행 오류', not_run:'미실행'};
let report, availableLayers = [], gdsData = null, inspectedFile = null, defaults;

async function api(path, data) {
  const response = await fetch(path, data === undefined ? {} : {
    method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(data)
  });
  const value = await response.json();
  if (!response.ok || value.error) throw Error(value.error || '요청 실패');
  return value;
}

function saveFile(value, name) {
  const url = URL.createObjectURL(new Blob([JSON.stringify(value,null,2)], {type:'application/json'}));
  const link = document.createElement('a');
  link.href = url; link.download = name; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function project() {
  const constraints = {rules:Array.from($('rules').children).map(row => {
    const [layer, datatype] = row.querySelector('[data-layer]').value.split('/').map(Number);
    const kind = row.querySelector('[data-kind]').value;
    return {kind, layer, datatype,
            [kind === 'min_area' ? 'value_um2' : 'value_um']:Number(row.querySelector('[data-value]').value)};
  })};
  if ($('maxWidth').value) constraints.max_width_um = Number($('maxWidth').value);
  if ($('maxHeight').value) constraints.max_height_um = Number($('maxHeight').value);
  return {schema_version:1, pdk:$('pdk').value, top:$('top').value, scope:$('scope').value,
          physical_checks:$('physical').checked,
          substrate:$('substrate').value, spice_units:$('units').value, project_constraints:constraints};
}

function remember() {
  try { localStorage.setItem(storageKey, JSON.stringify(project())); }
  catch (error) { $('settingsState').textContent = '브라우저 저장을 사용할 수 없습니다. JSON 저장을 이용하세요.'; }
}

function layerOptions(select, value) {
  select.replaceChildren();
  const layers = [...availableLayers];
  if (!layers.some(layer => `${layer.layer}/${layer.datatype}` === value)) {
    const [layer, datatype] = value.split('/').map(Number);
    layers.push({layer, datatype, name:''});
  }
  for (const layer of layers) {
    const option = document.createElement('option');
    option.value = `${layer.layer}/${layer.datatype}`;
    option.textContent = `${layer.name || 'GDS'} · ${option.value}`;
    select.appendChild(option);
  }
  select.value = value;
}

function addRule(rule = {kind:'min_width', layer:68, datatype:20, value_um:0.14}) {
  if ($('rules').children.length >= 64) throw Error('레이어 규칙은 최대 64개입니다.');
  const row = document.createElement('div');
  row.className = 'rule';
  row.innerHTML = '<label>레이어<select data-layer></select></label>' +
    '<label>규칙<select data-kind><option value="min_width">최소 폭</option><option value="min_space">최소 간격</option><option value="min_area">최소 면적</option></select></label>' +
    '<label><span data-unit>최소값 (µm)</span><input data-value type="number" min="0.000001" max="100000" step="any" required></label>' +
    '<button type="button" class="secondary">삭제</button>';
  layerOptions(row.querySelector('[data-layer]'), `${rule.layer}/${rule.datatype}`);
  row.querySelector('[data-kind]').value = rule.kind;
  row.querySelector('[data-value]').value = rule.value_um ?? rule.value_um2;
  const unit = () => row.querySelector('[data-unit]').textContent = row.querySelector('[data-kind]').value === 'min_area' ? '최소 면적 (µm²)' : '최소값 (µm)';
  row.querySelector('[data-kind]').onchange = () => { unit(); remember(); };
  unit();
  row.querySelector('button').onclick = () => { row.remove(); remember(); };
  $('rules').appendChild(row);
}

function apply(value) {
  $('physical').checked=!!value.physical_checks;
  $('pdk').value = value.pdk; $('top').value = value.top; $('scope').value = value.scope;
  $('substrate').value = value.substrate; $('units').value = value.spice_units;
  $('maxWidth').value = value.project_constraints.max_width_um ?? '';
  $('maxHeight').value = value.project_constraints.max_height_um ?? '';
  $('rules').replaceChildren(); value.project_constraints.rules.forEach(addRule);
}

async function encode(file) {
  return new Promise((resolve,reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result.split(',')[1]);
    reader.onerror = () => reject(Error('GDS 파일을 읽을 수 없습니다.'));
    reader.readAsDataURL(file);
  });
}

$('gds').onchange = async () => {
  const file = $('gds').files[0]; gdsData = null; inspectedFile = null;
  if (!file) return;
  $('go').disabled = true; $('layoutInfo').textContent = 'GDS 셀과 레이어를 읽는 중…';
  try {
    if (file.size > 20*1024*1024) throw Error('GDS 크기는 최대 20 MiB입니다.');
    const data = await encode(file), info = await api('/api/verification/inspect', {gds_base64:data});
    if ($('gds').files[0] !== file) return;
    gdsData = data; inspectedFile = file; availableLayers = info.layers;
    $('topCells').replaceChildren();
    for (const cell of info.top_cells) {
      const option = document.createElement('option'); option.value = cell.name; $('topCells').appendChild(option);
    }
    if (info.top_cells.length === 1 && !info.top_cells.some(cell => cell.name === $('top').value))
      $('top').value = info.top_cells[0].name;
    for (const select of $('rules').querySelectorAll('[data-layer]')) layerOptions(select, select.value);
    $('layoutInfo').textContent = `최상위 셀 ${info.top_cells.length}개 · 레이어 ${info.layers.length}개 · DBU ${info.dbu_um} µm`;
    $('go').disabled = false; remember();
  } catch (error) { if ($('gds').files[0] === file) $('layoutInfo').textContent = error.message; }
};

$('spice').onchange = async () => {
  const file = $('spice').files[0]; if (!file) return;
  try {
    if (file.size > 2*1024*1024) throw Error('SPICE 크기는 최대 2 MiB입니다.');
    const text = await file.text(), match = text.match(/^\s*\.subckt\s+\S+\s+([^\r\n]+)/im);
    if ($('spice').files[0] !== file) return;
    if (match) {
      const pins = match[1].split(/\s+/);
      const candidate = ['VNB','VSS','VGND','GND'].map(name => pins.find(pin => pin.toUpperCase() === name)).find(Boolean);
      if (candidate) {
        $('substrate').value = candidate;
        $('settingsState').textContent = `SPICE 핀에서 기판 net ${candidate}을 제안했습니다. 확인 후 실행하세요.`;
        remember();
      }
    }
  } catch (error) { $('settingsState').textContent = error.message; }
};

$('run').addEventListener('input', remember);
$('addRule').onclick = () => { try { addRule(); remember(); } catch (error) { $('settingsState').textContent = error.message; } };
$('export').onclick = async () => {
  try {
    const value = await api('/api/verification/settings', project());
    saveFile(value, 'verification-settings.json');
    $('settingsState').textContent = '설정을 JSON으로 저장했습니다. 파일 내용은 포함하지 않습니다.';
  } catch (error) { $('settingsState').textContent = error.message; }
};
$('import').onclick = () => $('settingsFile').click();
$('settingsFile').onchange = async () => {
  try {
    const file = $('settingsFile').files[0]; if (!file) return;
    if (file.size > 128*1024) throw Error('설정 JSON은 최대 128 KiB입니다.');
    const value = await api('/api/verification/settings', JSON.parse(await file.text()));
    apply(value); remember();
    $('settingsState').textContent = '프로젝트 설정을 적용했습니다.';
  } catch (error) { $('settingsState').textContent = `설정을 불러오지 못했습니다: ${error.message}`; }
  finally { $('settingsFile').value = ''; }
};
$('reset').onclick = () => { if (defaults) { apply(defaults); remember(); $('settingsState').textContent = 'PDK 기본값으로 초기화했습니다.'; } };

$('run').onsubmit = async event => {
  event.preventDefault(); $('go').disabled = true; $('result').hidden = true;
  $('state').textContent = '검사 중입니다. 검사별 최대 실행 시간은 5분입니다.';
  try {
    const file = $('gds').files[0], spice = $('spice').files[0];
    if (!gdsData || inspectedFile !== file) throw Error('GDS를 선택해 셀·레이어 읽기를 완료하세요.');
    if (spice && spice.size > 2*1024*1024) throw Error('SPICE 크기는 최대 2 MiB입니다.');
    const config = await api('/api/verification/settings', project());
    report = await api('/api/verification', {...config, gds_base64:gdsData, netlist:spice ? await spice.text() : null});
    $('identity').textContent = `${report.top} · ${report.engine_version} · ${report.created_at}`;
    $('checks').replaceChildren();
    for (const item of report.signoff.checklist) {
      const kind = item.check, check = report[kind] || item, row = document.createElement('tr');
      const details = check.reason || (kind === 'pex' ? `R: ${check.resistors} · C: ${check.capacitors}` : kind === 'antenna' ? `${check.feedback_count}개 피드백` : kind === 'lvs' ? `${check.circuits.length}개 회로 비교` : `${check.violations}개 위반`);
      for (const value of [kind.toUpperCase(), labels[check.status] || check.status, details]) {
        const td = document.createElement('td'); td.textContent = value; row.appendChild(td);
      }
      row.className = check.status; $('checks').appendChild(row);
    }
    $('detail').textContent = JSON.stringify(report,null,2); $('result').hidden = false;
    const ready = report.signoff.status === 'ready_for_review';
    $('gate').textContent = ready ? '검토 준비 완료 · 제조 sign-off 미인증' : `검토 보류: ${report.signoff.blocking_checks.join(', ')}`;
    $('state').textContent = ready ? '선택한 범위의 검사가 통과했습니다.' : '체크리스트를 확인하세요. 미실행·오류는 통과로 처리하지 않습니다.';
  } catch (error) { $('state').textContent = error.message; }
  finally { $('go').disabled = false; }
};
$('download').onclick = () => saveFile(report, `verification-${report.run_id}.json`);
$('evidence').onclick=async()=>{try{const response=await fetch('/api/verification/evidence/'+report.run_id);if(!response.ok)throw Error('검토 자료를 만들지 못했습니다.');const url=URL.createObjectURL(await response.blob()),a=document.createElement('a');a.href=url;a.download='evidence-'+report.run_id+'.zip';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}catch(e){$('gate').textContent=e.message;}};
$('pex').onclick=()=>{if(!report?.pex?.netlist){$('gate').textContent='PEX 검사를 포함하여 실행하세요.';return;}const url=URL.createObjectURL(new Blob([report.pex.netlist],{type:'text/plain'})),a=document.createElement('a');a.href=url;a.download='extracted.spice';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};

(async () => {
  try {
    const data = await api('/api/verification/catalog'), pdk = data.pdks[0];
    defaults = pdk.defaults; availableLayers = pdk.layers;
    $('deckState').textContent = Object.entries(pdk.checks).map(([name,ready]) => `${name.toUpperCase()}: ${ready ? '준비됨' : 'deck 설치 필요'}`).join(' · ');
    let saved; try { saved = localStorage.getItem(storageKey); } catch (error) {}
    if (saved) {
      try {
        apply(await api('/api/verification/settings', JSON.parse(saved)));
        $('settingsState').textContent = '이 브라우저의 이전 프로젝트 설정을 복원했습니다.';
      } catch (error) { apply(defaults); $('settingsState').textContent = '저장된 설정이 유효하지 않아 기본값을 적용했습니다.'; }
    } else apply(defaults);
  } catch (error) { $('deckState').textContent = error.message; }
})();

const panel = document.getElementById('verification-panel');
$('open').onclick = () => panel.showModal();
$('close').onclick = () => panel.close();
})();
