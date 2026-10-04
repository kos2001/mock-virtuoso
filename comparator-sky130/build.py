"""Reproducible SKY130 StrongARM demonstrator; preserves original mock cell."""
from pathlib import Path
import subprocess,json,hashlib,sys
import klayout.db as db
from mock_virtuoso import pdk
ROOT=Path(__file__).resolve().parents[1]; OUT=Path(__file__).resolve().parent
TOP='strongarm_sky130'; PDK=pdk.installed()
# Independent declared reference: reset internal and output nodes low-clock,
# regenerative evaluate high-clock. VINP>VINN => OUTP high, OUTN low.
DEVICES=[('tail','n',4,'tail','CLK','VSS','VSS'),
 ('inp','n',2,'xn','VINP','tail','VSS'),('inn','n',2,'xp','VINN','tail','VSS'),
 ('lnp','n',1,'OUTP','OUTN','xp','VSS'),('lnn','n',1,'OUTN','OUTP','xn','VSS'),
 ('lpp','p',1,'OUTP','OUTN','VDD','VDD'),('lpn','p',1,'OUTN','OUTP','VDD','VDD'),
 ('rxp','p',1,'xp','CLK','VDD','VDD'),('rxn','p',1,'xn','CLK','VDD','VDD'),
 ('rop','p',1,'OUTP','CLK','VDD','VDD'),('ron','p',1,'OUTN','CLK','VDD','VDD')]
PORTS=['VINP','VINN','CLK','OUTP','OUTN','VDD','VSS']; NETS=PORTS+['tail','xp','xn']
lines=[f'.subckt {TOP} '+ ' '.join(PORTS)]
for name,kind,w,*nets in DEVICES: lines.append(f'XM{name} '+ ' '.join(nets)+ f' sky130_fd_pr__{ "nfet" if kind=="n" else "pfet"}_01v8 w={w} l=0.15')
lines.append(f'.ends {TOP}'); (OUT/'reference.spice').write_text('\n'.join(lines)+'\n')
for kind,w in set((d[1],d[2]) for d in DEVICES):
 (OUT/f'{kind}{w}.mag').unlink(missing_ok=True)
script=['scalegrid 1 2',f'source {PDK}/libs.tech/magic/sky130A.tcl','snap internal']
for kind,w in sorted(set((d[1],d[2]) for d in DEVICES)):
 model='nfet' if kind=='n' else 'pfet'; name=f'{kind}{w}'
 script += [f'load {name}', 'box values 0 0 0 0',f'set pars [dict merge [sky130::sky130_fd_pr__{model}_01v8_defaults] {{w {w} l 0.15 doports 1}}]',f'sky130::sky130_fd_pr__{model}_01v8_draw $pars', f'save {name}',f'gds write {name}.gds']
script += ['quit -noprompt']; (OUT/'generate.tcl').write_text('\n'.join(script)+'\n')
r=subprocess.run([str(ROOT/'.tools/magic-install/bin/magic'),'-dnull','-noconsole','-T',str(PDK/'libs.tech/magic/sky130A.tech')],input='\n'.join(script),cwd=OUT,text=True,capture_output=True,timeout=90)
(OUT/'generation.log').write_text(r.stdout+r.stderr)
if r.returncode or not all((OUT/f'{k}{w}.gds').exists() for k,w in set((d[1],d[2]) for d in DEVICES)): raise RuntimeError(r.stdout+r.stderr)
l=db.Layout(); l.dbu=.001; top=l.create_cell(TOP)
def rect(cell,layer,x,y,w,h=None):
 h=h or w; cell.shapes(l.layer(*layer)).insert(db.Box(round((x-w/2)*1000),round((y-h/2)*1000),round((x+w/2)*1000),round((y+h/2)*1000)))
def wire(layer,pts,width):
 top.shapes(l.layer(*layer)).insert(db.Path([db.Point(round(x*1000),round(y*1000)) for x,y in pts],round(width*1000),round(width*500),round(width*500)))
def via1(x,y):
 rect(top,(68,20),x,y,.4);rect(top,(68,44),x,y,.15);rect(top,(69,20),x,y,.4)
def via2(x,y):
 rect(top,(69,20),x,y,.4);rect(top,(69,44),x,y,.2);rect(top,(70,20),x,y,.5)
masters={}; pins={}
for kind,w in sorted(set((d[1],d[2]) for d in DEVICES)):
 src=db.Layout();src.read(str(OUT/f'{kind}{w}.gds')); c=src.top_cell(); pin={}
 for i in src.layer_indexes():
  for s in c.shapes(i).each():
   if s.is_text():pin[s.text.string]=(s.text.x*src.dbu,s.text.y*src.dbu)
  for shape in list(c.shapes(i).each()):
   if shape.is_text(): c.shapes(i).erase(shape)
 dest=l.create_cell(f'{kind}{w}');dest.copy_tree(c); gx,gy=pin['G'];rect(dest,(68,20),gx,-gy,.34,.26);masters[(kind,w)]=dest;pins[(kind,w)]=pin
tracks={net:10+1.2*i for i,net in enumerate(NETS)}
connections={net:[] for net in NETS}
for i,(name,kind,w,*nets) in enumerate(DEVICES):
 xoff=4+8*i; c=masters[(kind,w)]; top.insert(db.CellInstArray(c.cell_index(),db.Trans(round(xoff*1000),0)))
 for port,net in zip(['D','G','S','B'],nets):
  px,py=pins[(kind,w)][port];x=px+xoff;y=py
  if port in ['D','S']:
   x=xoff+(-.8 if port=='D' else .8);wire((68,20),[(px+xoff,py),(x,py)],.24);via1(x,y)
  elif port=='G':
   rect(top,(68,20),x,y,.34,.26);rect(top,(68,44),x,y,.15);rect(top,(69,20),x,y,.4)
  else:
   # Generator guard has LI but no metal: add real mcon with enclosure.
   rect(top,(67,20),x,y,.34);rect(top,(67,44),x,y,.17);rect(top,(68,20),x,y,.4);via1(x,y)
   bx=xoff-2;wire((69,20),[(x,y),(bx,y)],.4);x=bx
  wire((69,20),[(x,y),(x,tracks[net])],.4);via2(x,tracks[net]);connections[net].append(x)
for net,y in tracks.items():
 left=min(connections[net]);right=max(connections[net]);wire((70,20),[(left,y),(right,y)] if left!=right else [(left-.25,y),(right+.25,y)],.5)
 if net in PORTS:
  top.shapes(l.layer(70,5)).insert(db.Text(net,db.Trans(round(left*1000),round(y*1000))))
l.write(str(OUT/f'{TOP}.gds'))
manifest={'top':TOP,'devices':len(DEVICES),'pdk_revision':pdk.revision(),'dbu_um':l.dbu,'ports':PORTS,'dimensions_um':[top.bbox().width()*l.dbu,top.bbox().height()*l.dbu], 'assumptions':{'vdd':1.8,'clock_hz':1e7,'common_mode_v':.9,'differential_v':[-.01,.01],'output_load_f':5e-15},'generator_sources':{str(p.relative_to(PDK)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [PDK/'libs.tech/magic/sky130A.tcl',PDK/'libs.tech/magic/sky130A.tech']},'inputs':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [OUT/'reference.spice',OUT/f'{TOP}.gds',OUT/'generate.tcl']},'note':'New declared reference; not claimed equivalent to original conceptual layout.'}
(OUT/'build.json').write_text(json.dumps(manifest,indent=2));print(json.dumps(manifest,indent=2))
