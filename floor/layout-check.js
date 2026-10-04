(() => {
  const $ = name => document.getElementById('layout-check-' + name);
  let report = null, running = false, polling = false, revision = 0;
  const selected = () => {
    const [library, cell] = document.getElementById('layout-cell').value.split('/');
    if (!library || !cell) throw Error('검사할 레이아웃 셀을 선택하세요.');
    return {library, cell, view:'layout'};
  };
  async function api(path, payload) {
    const response = await fetch(path, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload)});
    const data = await response.json();
    if (!response.ok || data.error) throw Error(data.error || '검사 요청 실패');
    return data;
  }
  function stale() {
    if (!report) return;
    report.stale = true;
    $('stale').hidden = false;
    if (report.external.run_id) window.dispatchEvent(new CustomEvent('floor-verification-result', {detail:{report:report.external, stale:true}}));
  }
  async function freshness() {
    if (!report || running || polling) return;
    polling = true;
    const previous = report;
    try {
      const target = selected();
      if (target.library !== report.target.library || target.cell !== report.target.cell) stale();
      const result = await api('/api/layout/status', {...previous.target, snapshot_sha256:previous.snapshot_sha256});
      if (report === previous && result.stale) stale();
    } catch (error) { if (report === previous) { stale(); $('state').textContent = error.message; } }
    finally { polling = false; }
  }
  $('open').onclick = () => {
    try { const target=selected(); $('target').textContent=target.library+'/'+target.cell+'/layout'; $('panel').showModal(); freshness(); }
    catch (error) { $('state').textContent=error.message; $('panel').showModal(); }
  };
  $('close').onclick = () => $('panel').close();
  for (const name of ['profile','spice','substrate','units','pex']) {
    $(name).addEventListener('change', () => { revision++; stale(); $('physical').hidden=$('profile').value !== 'sky130'; });
    $(name).addEventListener('input', () => { revision++; stale(); });
  }
  $('run').onclick = async () => {
    if (running) return;
    running=true; $('run').disabled=true; $('state').textContent='DB 읽기 · GDS 비교 · 선택한 검사를 실행 중입니다…';
    const started=revision;
    try {
      const target=selected(), file=$('spice').files[0];
      if (file && file.size > 2*1024*1024) throw Error('SPICE 크기는 최대 2 MiB입니다.');
      const payload={...target, profile:$('profile').value,
        netlist:file ? await file.text() : null,
        settings:{substrate:$('substrate').value, spice_units:$('units').value, physical_checks:$('pex').checked}};
      const result=await api('/api/layout/check', payload);
      report=result; $('target').textContent=target.library+'/'+target.cell+'/layout';
      if (started !== revision) report.stale=true;
      $('stale').hidden=!report.stale;
      $('result').hidden=false;
      const external=report.external, labels={pass:'통과',fail:'실패',error:'실행 오류',not_run:'미실행'};
      $('summary').textContent=[
        `대상: ${target.library}/${target.cell}/layout`,
        `도형 ${report.counts.shapes} · 인스턴스 ${report.counts.instances} · 하위 셀 포함 ${report.counts.cellviews}개 셀뷰 · DB 핀 ${report.counts.pins}`,
        `GDS 형상·계층 재읽기: ${labels[report.roundtrip.status]}`,
        `mockTech 검사: ${labels[report.mock_drc.status]} (${report.mock_drc.violations.length}개 위반 · 교육용)`,
        `PDK DRC: ${labels[external.drc?.status || 'not_run']} · LVS: ${labels[external.lvs?.status || 'not_run']} · PEX: ${labels[external.pex?.status || 'not_run']}`,
        '화면 렌더링·요구 기능/성능 일치: 별도 검증 필요',
        `DB 입력 SHA-256: ${report.snapshot_sha256}`, `GDS SHA-256: ${report.gds_sha256}`
      ].join('\n');
      const {gds_base64, ...detail}=report;
      $('detail').textContent=JSON.stringify(detail,null,2);
      $('evidence').hidden=!external.run_id;
      if (external.run_id) window.dispatchEvent(new CustomEvent('floor-verification-result', {detail:{report:external,stale:report.stale}}));
      $('state').textContent='검사가 완료되었습니다. 각 검사 상태를 확인하세요.';
    } catch (error) { stale(); $('state').textContent=error.message; }
    finally { running=false; $('run').disabled=false; freshness(); }
  };
  function save(blob, name) {
    const url=URL.createObjectURL(blob), link=document.createElement('a');
    link.href=url; link.download=name; link.click(); setTimeout(()=>URL.revokeObjectURL(url),1000);
  }
  $('gds').onclick=()=>{ if (report) save(new Blob([Uint8Array.from(atob(report.gds_base64), c=>c.charCodeAt(0))]), report.target.cell+'.gds'); };
  $('json').onclick=()=>{ if (report) { const {gds_base64,...data}=report; save(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}), 'layout-check-'+report.run_id+'.json'); } };
  $('evidence').onclick=async()=>{ try { const response=await fetch('/api/verification/evidence/'+report.external.run_id); if (!response.ok) throw Error('검증 자료 ZIP 다운로드 실패'); save(await response.blob(),'layout-evidence-'+report.external.run_id+'.zip'); } catch(error) { $('state').textContent=error.message; } };
  setInterval(freshness,3000);
})();
