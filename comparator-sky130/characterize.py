"""Real ngspice characterization; preserve raw waveforms and PDK hashes."""
from pathlib import Path
import subprocess,json,hashlib,argparse
from mock_virtuoso import pdk
from mock_virtuoso.simulation import read_raw
OUT=Path(__file__).resolve().parent
ap=argparse.ArgumentParser();ap.add_argument('--quick',action='store_true');ap.add_argument('--alternating',action='store_true');ap.add_argument('--mode',choices=['reference','pex'],default='reference');args=ap.parse_args()
reference=(OUT/'reference.spice').read_text(); results=[]
physical=None
if args.mode=='pex':
 physical=json.loads((OUT/'latest-verification.json').read_text())
 if any(physical.get(k,{}).get('status')!='pass' for k in ['drc','lvs','pex','antenna']): raise ValueError('PEX simulation requires all physical checks to pass')
 native=physical['pex']['netlist']
 # GDS labels become electrical nets but Magic does not mark them as ports.
 # This adapter exposes existing named nets; it changes no devices or R/C.
 ports='VINP VINN CLK OUTP OUTN VDD VSS'
 if '.subckt extracted\n' not in native: raise ValueError('Unexpected native PEX header')
 reference=native.replace('.subckt extracted\n','.subckt strongarm_sky130 '+ports+'\n')
 (OUT/'pex-dut.spice').write_text(reference)

for corner in (['tt'] if args.quick else pdk.CORNERS):
 model,meta=pdk.models(corner);mp=OUT/f'models-{corner}.spice';mp.write_text(model)
 for temp in ([27] if args.quick else [-40,27,125]):
  for dv in [-.01,.01]:
   name=f'{corner}-{temp}-{dv:+.3f}'+('-alternating' if args.alternating else '');work=OUT/('post-layout-simulation' if args.mode=='pex' else 'simulation')/name;work.mkdir(parents=True,exist_ok=True)
   vip=str(.9+dv/2);vin=str(.9-dv/2)
   if args.alternating:
    vip=f'PWL(0 {.9+dv/2} 99n {.9+dv/2} 100n {.9-dv/2} 199n {.9-dv/2} 200n {.9+dv/2})'
    vin=f'PWL(0 {.9-dv/2} 99n {.9-dv/2} 100n {.9+dv/2} 199n {.9+dv/2} 200n {.9-dv/2})'
   deck=f'''StrongARM SKY130 {name}
.include "{mp}"
{reference}
VDD VDD 0 1.8
VSS VSS 0 0
VIP VINP 0 {vip}
VIN VINN 0 {vin}
VCLK CLK 0 PULSE(0 1.8 25n .1n .1n 50n 100n)
XD VINP VINN CLK OUTP OUTN VDD VSS strongarm_sky130
CLP OUTP 0 5f
CLN OUTN 0 5f
.temp {temp}
.options filetype=ascii
.tran 20p 320n
.save v(CLK) v(OUTP) v(OUTN) i(VDD)
.end
'''
   (work/'input.cir').write_text(deck)
   r=subprocess.run(['/opt/homebrew/bin/ngspice','-n','-b','-r','output.raw','input.cir'],cwd=work,text=True,capture_output=True,timeout=120)
   (work/'ngspice.log').write_text(r.stdout+r.stderr)
   result={'case':name,'corner':corner,'temperature_c':temp,'differential_v':dv,'alternating':args.alternating,'reference_sha256':hashlib.sha256(reference.encode()).hexdigest(),'deck_sha256':hashlib.sha256(deck.encode()).hexdigest(),'pdk':meta,'status':'error'}
   if r.returncode:result['reason']=(r.stdout+r.stderr)[-2000:]
   else:
    raw=read_raw(work/'output.raw',full=True);cols={c['name']:c['real'] for c in raw['columns']};t=cols['time'];vp=cols['v(outp)'];vn=cols['v(outn)'];cycles=[]
    for start in [25e-9,125e-9,225e-9]:
     indices=[i for i,x in enumerate(t) if start+.05e-9<=x<start+49e-9];last=indices[-1];sign=(1 if dv>0 else -1)*(-1 if args.alternating and start==125e-9 else 1)
     settled=[i for i in indices if sign*(vp[i]-vn[i])>=1.44];delay=(t[settled[0]]-(start+.05e-9))*1e9 if settled else None
     reset=max(i for i,x in enumerate(t) if x<=start-1e-9)
     cycles.append({'reset_correct':vp[reset]>=1.62 and vn[reset]>=1.62,'outp_v':vp[last],'outn_v':vn[last],'correct':sign*(vp[last]-vn[last])>=1.44,'decision_delay_ns':delay})
    current=cols['i(vdd)'];energy=sum(-1.8*(current[i]+current[i-1])/2*(t[i]-t[i-1]) for i in range(1,len(t)) if t[i-1]>=100e-9 and t[i]<=300e-9)
    result.update(status='pass' if all(c['correct'] and c['reset_correct'] for c in cycles) else 'fail',cycles=cycles,average_power_uw=energy/200e-9*1e6,samples=raw['sample_count'])
   (work/'result.json').write_text(json.dumps(result,indent=2));results.append(result);print(name,result['status'],result.get('cycles'),flush=True)
summary={'scope':'Post-layout RC extracted DUT' if args.mode=='pex' else 'Independent reference schematic','engine':subprocess.run(['/opt/homebrew/bin/ngspice','--version'],text=True,capture_output=True).stdout.splitlines()[:6],'conditions':{'vdd_v':1.8,'clock_hz':1e7,'common_mode_v':.9,'load_f':5e-15,'criterion':'Correct differential polarity and >=1.44 V differential within 49 ns of evaluate edge','performance_acceptance_limits':'Not supplied; measured only','delay_definition':'CLK 50% rising edge to differential output >=80% VDD; sampled at <=20ps','power_definition':'DUT VDD supply power averaged over 100-300ns; ideal input/clock driver energy excluded'},'status':'pass' if results and all(r['status']=='pass' for r in results) else 'fail','cases':results}
if any(r['status']=='error' for r in results):
 summary['measured']={'status':'incomplete','reason':'One or more simulations failed; inspect case logs'}
else:
 summary['measured']={'delay_ns_min':min(c['decision_delay_ns'] for r in results for c in r.get('cycles',[]) if c['decision_delay_ns'] is not None),'delay_ns_max':max(c['decision_delay_ns'] for r in results for c in r.get('cycles',[]) if c['decision_delay_ns'] is not None),'power_uw_min':min(r['average_power_uw'] for r in results if 'average_power_uw' in r),'power_uw_max':max(r['average_power_uw'] for r in results if 'average_power_uw' in r)}
if physical: summary['physical_evidence']={'run_id':physical['run_id'],'gds_sha256':physical['inputs']['gds']['sha256'],'native_pex_sha256':hashlib.sha256(native.encode()).hexdigest(),'adapted_pex_sha256':hashlib.sha256(reference.encode()).hexdigest(),'adapter':'Expose seven existing named electrical nets as subcircuit ports; no device or RC changes.'}
(OUT/(('quick-' if args.quick else '')+('alternating-' if args.alternating else '')+('post-layout-' if args.mode=='pex' else '')+'characterization.json')).write_text(json.dumps(summary,indent=2))
