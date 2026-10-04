"""Validate evidence provenance and summarize actual measured checks."""
from pathlib import Path
import json,hashlib,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from mock_virtuoso.simulation import read_raw
OUT=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
physical=json.loads((OUT/'latest-verification.json').read_text());checks=['drc','lvs','pex','antenna']
assert all(physical[k]['status']=='pass' for k in checks)
assert sha(OUT/'strongarm_sky130.gds')==physical['inputs']['gds']['sha256']
assert sha(OUT/'reference.spice')==physical['inputs']['netlist']['sha256']
assert physical['extraction']['input_sha256']==physical['inputs']['gds']['sha256']
results={}
for mode,filename,folder in [('reference','characterization.json','simulation'),('pex','post-layout-characterization.json','post-layout-simulation')]:
 r=json.loads((OUT/filename).read_text());expected=sha(OUT/('reference.spice' if mode=='reference' else 'pex-dut.spice'))
 for c in r['cases']:
  assert c['reference_sha256']==expected
  work=OUT/folder/c['case'];assert sha(work/'input.cir')==c['deck_sha256']
  cols={x['name']:x['real'] for x in read_raw(work/'output.raw',full=True)['columns']};t=cols['time']
  for cycle,start in zip(c['cycles'],[25e-9,125e-9,225e-9]):
   i=max(i for i,x in enumerate(t) if x<=start-1e-9)
   cycle['reset_correct']=cols['v(outp)'][i]>=1.62 and cols['v(outn)'][i]>=1.62
  c['status']='pass' if all(x['correct'] and x['reset_correct'] for x in c['cycles']) else 'fail'
  c['raw_sha256']=sha(work/'output.raw');(work/'result.json').write_text(json.dumps(c,indent=2))
 assert all(c['status']=='pass' for c in r['cases'])
 (OUT/filename).write_text(json.dumps(r,indent=2))
 tt=next(c for c in r['cases'] if c['corner']=='tt' and c['temperature_c']==27 and c['differential_v']>0)
 results[mode]={'status':'pass','cases':len(r['cases']),'decisions':sum(len(c['cycles']) for c in r['cases']),'measured':r['measured'],'tt_27_positive':{'delay_ns':tt['cycles'][1]['decision_delay_ns'],'power_uw':tt['average_power_uw']},'artifact':filename,'artifact_sha256':sha(OUT/filename)}
alternating=json.loads((OUT/'quick-alternating-post-layout-characterization.json').read_text());assert alternating['status']=='pass'
roundtrip=json.loads((OUT/'roundtrip.json').read_text());assert roundtrip['status']=='pass'
summary={'target':'layout_gen/strongarm_sky130/layout','physical_run_id':physical['run_id'],'physical_directory':physical['directory'],'gds_sha256':physical['inputs']['gds']['sha256'],'reference_sha256':physical['inputs']['netlist']['sha256'],'pdk_revision':physical['extraction']['pdk_revision'],'tools':{'klayout':physical['engine_version'],'magic':physical['extraction']['engine_version'],'ngspice':alternating['engine']},'physical':{k:{a:physical[k][a] for a in ['status','violations','extracted_devices','devices','feedback_count'] if a in physical[k]} for k in checks},'geometry':roundtrip,'simulation':results,'alternating_input':{'status':'pass','cases':len(alternating['cases']),'decisions':6,'corner':'tt','temperature_c':27},'conditions':alternating['conditions'],'limits':['Performance limits were not supplied; results are measured under declared conditions.','Voltage fixed at 1.8 V; common-mode fixed at 0.9 V; differential input +/-10 mV.','Device mismatch, noise, offset distributions and full common-mode/clock-rate characterization not run.','Public PDK checks are not foundry-qualified sign-off.'],'original_design':'Original strongarm_comparator retained unchanged; this new cell uses a newly declared independent reference.'}
(OUT/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps({k:summary[k] for k in ['physical','simulation','alternating_input']},indent=2))
