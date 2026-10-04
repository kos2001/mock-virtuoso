from pathlib import Path
import sys,json
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import klayout.db as db
from tools.floor_skill import lane_port
from virtuoso_bridge import VirtuosoClient
from toolkit.layout_verification import read_snapshot,export_gds
p=Path(__file__).resolve().parent
client=VirtuosoClient.local(port=lane_port(p.parent/'.tools/layout-check-lanes.env','request'),timeout=45)
snapshot=read_snapshot(client,{'library':'layout_gen','cell':'strongarm_sky130'})
(p/'snapshot.json').write_text(json.dumps(snapshot,indent=2))
export_gds(snapshot,'sky130',p/'floor-export.gds')
a=db.Layout();a.read(str(p/'strongarm_sky130.gds'));b=db.Layout();b.read(str(p/'floor-export.gds'))
checks=[]
for info in a.layer_infos():
 ra=db.Region(a.top_cell().begin_shapes_rec(a.layer(info))); rb=db.Region(b.cell('strongarm_sky130').begin_shapes_rec(b.layer(info))).transformed(db.ICplxTrans(b.dbu/a.dbu,0,False,0,0))
 checks.append({'layer':info.layer,'datatype':info.datatype,'xor_area_dbu2':(ra^rb).area()})
assert all(c['xor_area_dbu2']==0 for c in checks),'Import/export changed physical geometry'
root=snapshot['cells'][snapshot['root']];assert len(root['nets'])==7 and sum(len(n['pins']) for n in root['nets'])==7
result={'status':'pass','scope':'Generated GDS -> live mock DB -> GDS physical polygon XOR on all layers','snapshot_sha256':snapshot['snapshot_sha256'],'shape_count':len(root['shapes']),'bbox_um':root['bbox'],'pins':7,'layers':checks}
(p/'roundtrip.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
