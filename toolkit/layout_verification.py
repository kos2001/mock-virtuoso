"""Tie a verification run to one immutable snapshot of the displayed DB cell."""
import base64
import hashlib
import json
import math
from pathlib import Path
import re
import uuid

from mock_virtuoso.db.objects import CellView, Shape
from mock_virtuoso.db.geometry import transform_point, transform_bbox
from mock_virtuoso.domain.drc import check
from mock_virtuoso.skill.values import skill_repr
from toolkit import verification_service
from toolkit.standard_cell_layouts import LAYERS

ROOT = Path(__file__).resolve().parents[1]
DBU = 0.0001  # micrometres; off-grid data is refused, never silently rounded.
ORIENTS = {"R0": (0, False), "R90": (1, False), "R180": (2, False),
           "R270": (3, False), "MX": (0, True), "MY": (2, True),
           "MXR90": (1, True), "MYR90": (3, True)}


def read_snapshot(client, payload):
    if not isinstance(payload, dict):
        raise ValueError("Expected a JSON object")
    args = [payload.get("library"), payload.get("cell"), payload.get("view", "layout")]
    if not all(isinstance(a, str) and 0 < len(a) <= 256 for a in args) or args[2] != "layout":
        raise ValueError("Select a library/cell/layout target")
    result = client.execute_skill("mockLayoutSnapshot(" + " ".join(map(skill_repr, args)) + ")")
    if result.status.value != "success":
        raise ValueError("Layout snapshot failed: " + str(result.errors))
    data = json.loads(result.output)
    return json.loads(data) if isinstance(data, str) else data


def status(client, payload):
    data = read_snapshot(client, payload)
    return {"target": data["target"], "snapshot_sha256": data["snapshot_sha256"],
            "stale": data["snapshot_sha256"] != payload.get("snapshot_sha256")}


def canvas_geometry(snapshot):
    """Use the same snapshot fields for display, including path widths and hierarchy."""
    def shape_row(s):
        return {"kind": "shape", "objType": s["objType"], "layer": s["lpp"][0],
                "purpose": s["lpp"][1], "bbox": s["bBox"], "points": s["points"],
                "xy": s["xy"], "orient": s["orient"], "text": s["theLabel"], "width": s["width"]}

    def flatten(key):
        record = snapshot["cells"][key]
        rows = [shape_row(s) for s in record["shapes"]]
        for inst in record["instances"]:
            for row in flatten(inst["master"]):
                row = dict(row)
                row["bbox"] = transform_bbox(row["bbox"], inst["xy"], inst["orient"])
                if row["points"]:
                    row["points"] = [transform_point(p, inst["xy"], inst["orient"]) for p in row["points"]]
                if row["xy"]:
                    row["xy"] = transform_point(row["xy"], inst["xy"], inst["orient"])
                rows.append(row)
                if len(rows) > 100000:
                    raise ValueError("Canvas hierarchy exceeds 100000 shapes")
        return rows

    root = snapshot["cells"][snapshot["root"]]
    rows, masters = [shape_row(s) for s in root["shapes"]], {}
    for inst in root["instances"]:
        lib, cell, view = inst["master"].split("/")
        masters[f"{lib}/{cell}"] = flatten(inst["master"])
        rows.append({"kind": "instance", "name": inst["name"], "lib": lib, "cell": cell,
                     "view": view, "xy": inst["xy"], "orient": inst["orient"],
                     "bbox": transform_bbox(snapshot["cells"][inst["master"]]["bbox"], inst["xy"], inst["orient"])})
    return {"ok": True, "rows": rows, "masters": masters, "snapshot_sha256": snapshot["snapshot_sha256"]}


def layer_pair(lpp, profile):
    name, purpose = lpp
    if profile == "mockTech":
        names = {name: i + 1 for i, name in enumerate(("nwell", "diff", "poly", "met1", "met2", "met3", "text"))}
        purposes = {"drawing": 0, "pin": 1, "label": 2}
        if name in names and purpose in purposes:
            return names[name], purposes[purpose]
    elif profile == "sky130":
        number = next((pair[0] for pair, layer in LAYERS.items() if layer == name), None)
        if number is None:
            match = re.fullmatch(r"gds_(\d+)_(\d+)", name)
            if match:
                number = int(match[1])
        datatype = {"drawing": next((pair[1] for pair, layer in LAYERS.items() if layer == name), 20),
                    "pin": 16, "label": 5}.get(purpose)
        match = re.fullmatch(r"gds_(\d+)", purpose)
        if match:
            datatype = int(match[1])
        if number is not None and datatype is not None and 0 <= number <= 65535 and 0 <= datatype <= 65535:
            return number, datatype
    raise ValueError(f"No explicit {profile} GDS mapping for {name}/{purpose}")


def export_gds(snapshot, profile, path):
    import klayout.db as db
    if profile not in ("mockTech", "sky130"):
        raise ValueError("Choose mockTech or explicit SKY130 layer mapping")
    layout = db.Layout()
    layout.dbu = DBU
    top = snapshot["target"]["cell"]
    names = {key: top if key == snapshot["root"] else f"mv_child_{i}"
             for i, key in enumerate(snapshot["cells"])}
    names = {key: name if key == snapshot["root"] or name != top else "_" + name
             for key, name in names.items()}
    cells = {key: layout.create_cell(name) for key, name in names.items()}

    def grid(v):
        v = float(v) / DBU
        if not math.isfinite(v) or abs(v - round(v)) > 1e-6 or abs(v) >= 2**31:
            raise ValueError("Coordinates/width exceed GDS bounds or the 0.0001 µm export grid")
        return round(v)

    def point(p):
        return db.Point(*map(grid, p))

    def trans(orient, xy):
        if orient not in ORIENTS:
            raise ValueError("Unknown layout orientation")
        angle, mirror = ORIENTS[orient]
        return db.Trans(angle, mirror, *map(grid, xy))

    shape_count = 0
    for key, record in snapshot["cells"].items():
        cell = cells[key]
        for s in record["shapes"]:
            shape_count += 1
            if s["viaDef"] is not None:
                raise ValueError("Mock vias have no physical cut/enclosure stack; export real via geometry first")
            layer = layout.layer(*layer_pair(s["lpp"], profile))
            kind = s["objType"]
            if kind == "rect":
                shape = db.Box(point(s["bBox"][0]), point(s["bBox"][1]))
            elif kind == "polygon":
                shape = db.Polygon([point(p) for p in s["points"]])
            elif kind == "path":
                shape = db.Path([point(p) for p in s["points"]], grid(s["width"]),
                                grid(s["width"] / 2), grid(s["width"] / 2))
            elif kind == "label":
                shape = db.Text(s["theLabel"], trans(s["orient"] or "R0", s["xy"]))
            else:
                raise ValueError(f"Unsupported GDS shape: {kind}")
            cell.shapes(layer).insert(shape)
        for inst in record["instances"]:
            if inst["params"]:
                raise ValueError("Unresolved parameterized instances cannot be exported")
            cell.insert(db.CellInstArray(cells[inst["master"]].cell_index(), trans(inst["orient"], inst["xy"])))
    if shape_count == 0:
        raise ValueError("Empty layout cannot pass verification")
    if not any(db.Region(cells[snapshot["root"]].begin_shapes_rec(layer)).area() > 0
               for layer in layout.layer_indexes()):
        raise ValueError("Empty physical geometry cannot pass verification")
    layout.write(str(path))
    restored = db.Layout()
    restored.read(str(path))
    if restored.dbu != layout.dbu or restored.cells() != layout.cells():
        raise ValueError("GDS readback changed the database unit or cell count")
    if sorted(str(info) for info in restored.layer_infos()) != sorted(str(info) for info in layout.layer_infos()):
        raise ValueError("GDS readback changed the layer mapping")
    for key, cell in cells.items():
        other = restored.cell(names[key])
        if other is None or cell.child_instances() != other.child_instances():
            raise ValueError("GDS readback changed the hierarchy")
        for info in layout.layer_infos():
            before = cell.shapes(layout.layer(info))
            after = other.shapes(restored.layer(info))
            a = db.Region([s.polygon for s in before.each() if not s.is_text()])
            b = db.Region([s.polygon for s in after.each() if not s.is_text()])
            texts = lambda shapes: sorted((s.text.string, str(s.text.trans)) for s in shapes.each() if s.is_text())
            if not (a ^ b).is_empty() or texts(before) != texts(after):
                raise ValueError("GDS readback geometry/label mismatch")
        original = sorted((i.cell.name, str(i.trans)) for i in cell.each_inst())
        recovered = sorted((i.cell.name, str(i.trans)) for i in other.each_inst())
        if original != recovered:
            raise ValueError("GDS readback changed instance transforms")
    return {"status": "pass", "dbu_um": DBU, "top": top,
            "scope": "GDS geometry, labels and hierarchy roundtrip; renderer not checked"}


def verify(client, payload):
    snapshot = read_snapshot(client, payload)
    profile = payload.get("profile", "mockTech")
    run_id = uuid.uuid4().hex
    directory = ROOT / "layout-runs" / run_id
    directory.mkdir(parents=True)
    (directory / "snapshot.json").write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
    path = directory / "layout.gds"
    roundtrip = export_gds(snapshot, profile, path)
    violations = []
    for key, cell in snapshot["cells"].items():
        cv = CellView("snapshot", key, "layout", "maskLayout", "r")
        for s in cell["shapes"]:
            cv.shapes.append(Shape(s["objType"], *s["lpp"], bbox=s["bBox"]))
        violations.extend({"cell": key, "message": str(v), "severity": v.severity} for v in check(cv))
    root = snapshot["cells"][snapshot["root"]]
    report = {"run_id": run_id, "target": snapshot["target"],
              "snapshot_sha256": snapshot["snapshot_sha256"], "profile": profile,
              "counts": {"cellviews": len(snapshot["cells"]), "shapes": len(root["shapes"]),
                         "instances": len(root["instances"]), "nets": len(root["nets"]),
                         "pins": sum(len(n["pins"]) for n in root["nets"])},
              "bbox": root["bbox"], "roundtrip": roundtrip,
              "mock_drc": {"status": "fail" if violations else "pass", "violations": violations,
                           "scope": "mockTech bounding-box checks per cell; inter-instance spacing not checked"},
              "renderer": {"status": "not_run"},
              "connectivity": {"status": "not_run", "reason": "Named DB nets/pins are readback evidence; electrical equivalence requires LVS"},
              "functional": {"status": "not_run", "reason": "Run the circuit review/PEX comparison with project acceptance limits"},
              "external": {"status": "not_run", "reason": "mockTech export has no foundry PDK mapping"},
              "gds_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
              "directory": str(directory)}
    if profile == "sky130":
        settings = payload.get("settings", {})
        if not isinstance(settings, dict):
            raise ValueError("Expected verification settings")
        external = verification_service.verify_upload({**settings, "top": roundtrip["top"],
            "gds_base64": base64.b64encode(path.read_bytes()).decode(), "netlist": payload.get("netlist")})
        report["external"] = external
        # Retain the source snapshot next to the immutable external GDS/decks/logs.
        external_path = Path(external["directory"])
        (external_path / "layout-snapshot.json").write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
        external["source_layout"] = {"target": snapshot["target"], "snapshot_sha256": snapshot["snapshot_sha256"],
                                     "gds_sha256": report["gds_sha256"]}
        (external_path / "result.json").write_text(json.dumps(external, indent=2), encoding="utf-8")
    report["stale"] = status(client, {**snapshot["target"], "snapshot_sha256": snapshot["snapshot_sha256"]})["stale"]
    (directory / "result.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return {**report, "gds_base64": base64.b64encode(path.read_bytes()).decode()}
