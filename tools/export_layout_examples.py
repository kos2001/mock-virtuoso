"""Publish pinned SKY130 examples and native-geometry SVG previews in the repo."""
import hashlib
from html import escape
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from toolkit.standard_cell_layouts import CELLS, REVISION, geometry

COLORS = {'nwell':'#c9b2e8','nsdm':'#92ca92','psdm':'#dcadbf','diff':'#4bab69','tap':'#479783','poly':'#d54e52',
          'licon1':'#444444','li1':'#bd8b46','mcon':'#384958','met1':'#469cda',
          'via':'#17477b','met2':'#aa66cf'}


def preview(path, name):
    shapes = geometry(path)
    polygons = [s for s in shapes if s['type']=='polygon' and s['layer'] in COLORS and s['purpose'] in ('drawing','gds_44')]
    points = [p for s in polygons for p in s['points']]
    xmin,ymin = [min(p[i] for p in points) for i in (0,1)]
    xmax,ymax = [max(p[i] for p in points) for i in (0,1)]
    margin=.25
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="600" height="600" viewBox="{xmin-margin} {-ymax-margin} {xmax-xmin+2*margin} {ymax-ymin+2*margin}">',
           f'<title>{escape(name)} — SKY130 layout</title>',
           f'<rect x="{xmin-margin}" y="{-ymax-margin}" width="{xmax-xmin+2*margin}" height="{ymax-ymin+2*margin}" fill="#f8fafc"/>']
    order = list(COLORS)
    for shape in sorted(polygons,key=lambda s:order.index(s['layer'])):
        vertices = ' '.join(f'{x:.6g},{-y:.6g}' for x,y in shape['points'])
        color = COLORS[shape['layer']]
        svg.append(f'<polygon points="{vertices}" fill="{color}" fill-opacity="0.58" stroke="{color}" stroke-width="0.009"/>')
    for shape in shapes:
        if shape['type']=='label':
            x,y = shape['xy']
            svg.append(f'<text x="{x}" y="{-y}" text-anchor="middle" dominant-baseline="middle" font-family="sans-serif" font-size="0.10" fill="#101828" stroke="#fff" stroke-width="0.022" paint-order="stroke">{escape(shape["text"])}</text>')
    svg.append('</svg>')
    return '\n'.join(svg)+'\n'


def main():
    source = ROOT/'.tools/standard-cells'
    target = ROOT/'examples/sky130'
    target.mkdir(parents=True,exist_ok=True)
    manifest = json.loads((source/'sources.json').read_text(encoding='utf-8'))
    if manifest['revision'] != REVISION:
        raise ValueError('Unexpected SKY130 source revision')
    names = ['LICENSE']+[f'sky130_fd_sc_hd__{kind}_1.{suffix}' for kind in CELLS.values() for suffix in ('gds','spice')]
    for name in names:
        if hashlib.sha256((source/name).read_bytes()).hexdigest()!=manifest['files'][name]['sha256']:
            raise ValueError('Source hash mismatch: '+name)
        shutil.copyfile(source/name,target/name)
    (target/'sources.json').write_bytes((json.dumps(manifest,indent=2)+'\n').encode('utf-8'))
    rows=[]
    for cell,kind in CELLS.items():
        base=f'sky130_fd_sc_hd__{kind}_1'
        (target/(cell+'.svg')).write_text(preview(target/(base+'.gds'),cell),encoding='utf-8')
        rows.append(f'| {cell} | [{base}]({base}.gds) | [SPICE]({base}.spice) | [Preview]({cell}.svg) |')
    text='''# SKY130 standard-cell layouts

These are the 12 real layouts loaded into `SKY130_EXAMPLES` in this project.
The GDS and reference SPICE are **unchanged public SkyWater library assets**,
not newly designed or independently sign-off-qualified cells.
SVG previews are generated here from the GDS polygons and pin labels.

Source: [google/skywater-pdk-libs-sky130_fd_sc_hd](https://github.com/google/skywater-pdk-libs-sky130_fd_sc_hd)
at commit `'''+REVISION+'''`. See [LICENSE](LICENSE) (Apache-2.0)
and [sources.json](sources.json) for per-file URLs and SHA-256 hashes.
Original copyright notices are retained in the SPICE files.

| Drawing cell | GDS / native top cell | Reference | View |
|---|---|---|---|
'''+ '\n'.join(rows)+'''

![INV layout](INV_X1.svg)
![DFF layout](DFF_X1.svg)

Open a GDS in KLayout to inspect all layers. SVG colors are illustrative;
they are not a rule check or electrical-connectivity proof.
The Design Floor loads these bundled files at startup when KLayout's Python
package is installed. Existing cells are preserved. No download is required.

For DRC/LVS, upload the matching GDS and SPICE, use the exact native top-cell
name above, `VNB` as substrate net, and SKY130 micron dimensions.
Run the installed rule decks to establish the result for your chosen scope.
Simulation editor examples are separate educational circuits, so this package
does not assert that their transistor sizing matches these layouts.

Regenerate previews and the bundle after fetching the pinned source cache:

```powershell
.venv/Scripts/python.exe tools/export_layout_examples.py
```
'''
    (target/'README.md').write_text(text,encoding='utf-8')
    print(f'Published {len(CELLS)} GDS/SPICE pairs and SVG previews in {target}')


if __name__=='__main__':
    main()
