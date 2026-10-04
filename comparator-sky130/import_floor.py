from pathlib import Path
import sys,json,subprocess
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from toolkit.standard_cell_layouts import geometry
OUT=Path(__file__).resolve().parent;ROOT=OUT.parent
shapes=geometry(OUT/'strongarm_sky130.gds');q=json.dumps
pt=lambda p:'list('+' '.join(f'{v:.12g}' for v in p)+')'
lines=['if(ddGetObj("layout_gen" "strongarm_sky130") then "existing" else','let((cv net pin) cv=dbOpenCellViewByType("layout_gen" "strongarm_sky130" "layout" "maskLayout" "a")']
for s in shapes:
 lpp=f'list({q(s["layer"])} {q(s["purpose"])})'
 if s['type']=='label':
  lines.append(f'dbCreateLabel(cv {lpp} {pt(s["xy"])} {q(s["text"])} "centerCenter" "R0" "roman" 0.12)')
  x,y=s['xy'];name=s['text'];direction='inputOutput' if name in ['VDD','VSS'] else ('output' if name.startswith('OUT') else 'input')
  lines.extend([f'net=dbCreateNet(cv {q(name)})',f'dbCreateTerm(net {q(name)} {q(direction)})',f'pin=dbCreateRect(cv list("met3" "drawing") list({pt([x-.2,y-.2])} {pt([x+.2,y+.2])}))','dbCreatePin(net pin)'])
 else:lines.append(f'dbCreatePolygon(cv {lpp} list('+ ' '.join(pt(p) for p in s['points'])+'))')
lines+=['dbSave(cv) sprintf(nil "%d shapes %d nets %d terminals bBox %L" length(cv~>shapes) length(cv~>nets) length(cv~>terminals) cv~>bBox)))']
script='\n'.join(lines);(OUT/'import.il').write_text(script)
r=subprocess.run([str(ROOT/'.venv/bin/python'),str(ROOT/'tools/floor_skill.py'),'--env',str(ROOT/'.tools/layout-check-lanes.env'),'-p','request','--stdin'],input=script,text=True,capture_output=True,timeout=45)
print(r.stdout);print(r.stderr);r.check_returncode()
print('Expected shapes',len(shapes)+7)
