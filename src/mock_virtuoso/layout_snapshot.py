"""Read-only, complete hierarchy snapshots; no cellview open or creation."""
import hashlib
import json

from mock_virtuoso.skill.errors import SkillError
from mock_virtuoso.skill.values import NIL


def snapshot(design, library, cell, view="layout"):
    target = {"library": library, "cell": cell, "view": view}
    root = design.find_cellview(library, cell, view)
    if root is None:
        raise SkillError("Layout cell does not exist")
    cells, active = {}, set()

    def key(cv):
        return "/".join(cv.get_prop(p) for p in ("libName", "cellName", "viewName"))

    def value(v):
        if v is NIL:
            return None
        if isinstance(v, (list, tuple)):
            return [value(x) for x in v]
        if isinstance(v, dict):
            return {k: value(x) for k, x in v.items()}
        if not isinstance(v, (str, int, float, bool, type(None))):
            raise SkillError("Unsupported object in layout snapshot")
        return v

    def visit(cv):
        name = key(cv)
        if name in active:
            raise SkillError("Cyclic layout hierarchy")
        if name in cells:
            return name
        if len(cells) >= 256:
            raise SkillError("Layout snapshot exceeds 256 cellviews")
        active.add(name)
        shapes = cv.shapes
        shape_index = {id(s): i for i, s in enumerate(shapes)}
        record = {"key": name, "shapes": [], "instances": [], "nets": [], "bbox": cv.bbox}
        cells[name] = record
        for shape in shapes:
            data = {p: value(shape.get_prop(p)) for p in
                    ("objType", "lpp", "bBox", "points", "xy", "orient", "theLabel", "width")}
            net = shape.get_prop("net")
            via = shape.get_prop("viaDef")
            data["net"] = None if net is NIL else net.name
            data["viaDef"] = None if via is NIL else via.name
            record["shapes"].append(data)
        for net in cv.nets:
            record["nets"].append({"name": net.name,
                "terminals": [{"name": t.name, "direction": t.get_prop("direction")}
                              for t in net.get_prop("terminals")],
                "pins": [{"name": p.name, "shape": shape_index.get(id(p.get_prop("fig")))}
                         for p in net.get_prop("pins")]})
        for inst in cv.instances:
            master = inst.get_prop("master")
            if master is NIL:
                raise SkillError("Layout instance has no master")
            record["instances"].append({"name": inst.get_prop("name"), "master": visit(master),
                "xy": value(inst.get_prop("xy")), "orient": inst.get_prop("orient"),
                "params": value(inst.params)})
        active.remove(name)
        return name

    result = {"schema_version": 1, "backend": "mock-virtuoso", "target": target,
              "root": visit(root), "cells": cells}
    encoded = json.dumps(result, sort_keys=True, separators=(",", ":"), allow_nan=False)
    if len(encoded.encode()) > 16 * 1024 * 1024:
        raise SkillError("Layout snapshot exceeds 16 MiB")
    result["snapshot_sha256"] = hashlib.sha256(encoded.encode()).hexdigest()
    return result
