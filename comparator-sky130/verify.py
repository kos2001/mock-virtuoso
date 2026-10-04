from pathlib import Path
import json,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from mock_virtuoso.verification import run_verification
from toolkit.verification_service import find_klayout
p=Path(__file__).resolve().parent
r=run_verification(executable=find_klayout(),gds=p/'strongarm_sky130.gds',top='strongarm_sky130',decks=p.parent/'.tools/sky130',output=p.parent/'verification-runs',netlist=p/'reference.spice',substrate='VSS',physical_checks=True,timeout=120)
(p/'latest-verification.json').write_text(json.dumps(r,indent=2));print(json.dumps({'directory':r['directory'],'checks':{k:{a:r.get(k,{}).get(a) for a in ['status','violations','extracted_devices','devices','reason']} for k in ['drc','lvs','pex','antenna']}},indent=2))
