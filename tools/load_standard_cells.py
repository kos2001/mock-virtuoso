"""Fetch and load real SKY130 cell layouts through an existing Design Floor lane."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from toolkit.standard_cell_layouts import bundled_directory, fetch, populate


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fetch',action='store_true')
    parser.add_argument('--port',type=int,help='Existing bridge lane port; defaults to floor/lanes.env cells lane')
    args=parser.parse_args()
    directory=ROOT/'.tools/standard-cells' if args.fetch else bundled_directory(ROOT)
    if args.fetch or not (directory/'sources.json').is_file():
        fetch(directory)
    port=args.port
    if port is None:
        settings=dict(line.split('=',1) for line in (ROOT/'floor/lanes.env').read_text(encoding='utf-8').splitlines() if '=' in line and not line.startswith('#'))
        port=int(settings['VB_LOCAL_PORT_cells'])
    from virtuoso_bridge import VirtuosoClient
    report=populate(VirtuosoClient.local(port=port),directory)
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    main()
