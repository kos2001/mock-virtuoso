"""Import pinned public SKY130 standard-cell GDS into the existing mock DB."""
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen

REVISION = 'ac7fb61f06e6470b94e8afdf7c25268f62fbd7b1'
BASE = f'https://raw.githubusercontent.com/google/skywater-pdk-libs-sky130_fd_sc_hd/{REVISION}/'
CELLS = {'INV_X1': 'inv', 'BUF_X1': 'buf', 'NAND2_X1': 'nand2',
         'NOR2_X1': 'nor2', 'AND2_X1': 'and2', 'OR2_X1': 'or2',
         'XOR2_X1': 'xor2', 'XNOR2_X1': 'xnor2', 'MUX2_X1': 'mux2',
         'AOI21_X1': 'a21oi', 'OAI21_X1': 'o21ai', 'DFF_X1': 'dfxtp'}
LIBRARY = 'SKY130_EXAMPLES'


def bundled_directory(root):
    """Prefer versioned examples, falling back to the historical local cache."""
    bundled = Path(root)/'examples/sky130'
    return bundled if (bundled/'sources.json').is_file() else Path(root)/'.tools/standard-cells'


LAYERS = {(64,20):'nwell', (65,20):'diff', (65,44):'tap', (66,20):'poly',
          (66,44):'licon1', (67,20):'li1', (67,44):'mcon', (68,20):'met1',
          (68,44):'via', (69,20):'met2', (69,44):'via2', (70,20):'met3',
          (70,44):'via3', (71,20):'met4', (71,44):'via4', (72,20):'met5',
          (93,44):'nsdm', (94,20):'psdm', (235,4):'boundary'}


def fetch(directory):
    """Keep exact upstream GDS, reference SPICE, license and file hashes."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    sources = {}
    for path in ['LICENSE'] + [f'cells/{kind}/sky130_fd_sc_hd__{kind}_1.{ext}'
                              for kind in CELLS.values() for ext in ('gds','spice')]:
        target = directory / Path(path).name
        with urlopen(BASE + path, timeout=45) as response:
            data = response.read()
        target.write_bytes(data)
        sources[target.name] = {'url': BASE + path, 'sha256': hashlib.sha256(data).hexdigest()}
    (directory / 'sources.json').write_text(json.dumps({'revision': REVISION, 'files': sources}, indent=2), encoding='utf-8')


def geometry(path):
    import klayout.db as db
    layout = db.Layout()
    layout.read(str(path))
    top = layout.top_cell()
    if top is None:
        raise ValueError('GDS must have one top cell')
    top.flatten(True)
    shapes = []
    for info in layout.layer_infos():
        layer = LAYERS.get((info.layer, info.datatype))
        if not layer:
            layer = LAYERS.get((info.layer,20)) if info.datatype in (5,16) else None
        layer = layer or f'gds_{info.layer}_{info.datatype}'
        purpose = {20:'drawing',16:'pin',5:'label'}.get(info.datatype,f'gds_{info.datatype}')
        region = db.Region()
        for shape in top.shapes(layout.layer(info)).each():
            if shape.is_text():
                text = shape.text
                shapes.append({'type':'label','layer':layer,'purpose':purpose,
                               'xy':[text.x*layout.dbu,text.y*layout.dbu],'text':text.string})
            elif shape.is_box() or shape.is_polygon() or shape.is_path():
                region.insert(shape.polygon)
        # Decompose holes instead of replacing concave shapes with bounding boxes.
        for polygon in region.decompose_trapezoids().each():
            shapes.append({'type':'polygon','layer':layer,'purpose':purpose,
                           'points':[[p.x*layout.dbu,p.y*layout.dbu] for p in polygon.each_point_hull()]})
    return shapes


def skill_for(cell, shapes):
    if cell not in CELLS:
        raise ValueError('Unknown standard cell')
    quote = lambda value: json.dumps(value, ensure_ascii=True)
    point = lambda p: 'list(' + ' '.join(f'{v:.12g}' for v in p) + ')'
    # Existing cells are intentionally preserved. A second load is a no-op.
    lines = [f'if(ddGetObj("{LIBRARY}" "{cell}") then "existing" else',
             f'let((cv) cv = dbOpenCellViewByType("{LIBRARY}" "{cell}" "layout" "maskLayout" "a")']
    for shape in shapes:
        lpp = f'list({quote(shape["layer"])} {quote(shape["purpose"])})'
        if shape['type'] == 'label':
            lines.append(f'dbCreateLabel(cv {lpp} {point(shape["xy"])} {quote(shape["text"])} "centerCenter" "R0" "roman" 0.12)')
        else:
            points = 'list(' + ' '.join(point(p) for p in shape['points']) + ')'
            lines.append(f'dbCreatePolygon(cv {lpp} {points})')
    lines += ['dbSave(cv) "created"))']
    return '\n'.join(lines)


def populate(client, directory):
    directory = Path(directory)
    manifest = json.loads((directory / 'sources.json').read_text(encoding='utf-8'))
    prepared = []
    for name, kind in CELLS.items():
        path = directory / f'sky130_fd_sc_hd__{kind}_1.gds'
        if hashlib.sha256(path.read_bytes()).hexdigest() != manifest['files'][path.name]['sha256']:
            raise ValueError(f'GDS hash mismatch: {path.name}')
        shapes = geometry(path)
        if not shapes:
            raise ValueError(f'Empty geometry: {name}')
        prepared.append((name, shapes, skill_for(name, shapes)))
    report = []
    for name, shapes, skill in prepared:
        result = client.execute_skill(skill)
        if result.status.value != 'success':
            raise RuntimeError(f'{name}: {result.errors}')
        report.append({'library':LIBRARY,'cell':name,'shapes':len(shapes),'result':result.output})
    return report
