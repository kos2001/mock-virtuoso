"""Validated, declarative project constraints evaluated by KLayout geometry.

These constraints supplement the installed PDK deck; they never replace it.
No uploaded rule text is interpreted as Python, Ruby or SKILL.
"""
from __future__ import annotations

import math


def validate_constraints(value):
    if value is None:
        return {"rules": []}
    if not isinstance(value, dict):
        raise ValueError("Project constraints must be an object")
    unknown = set(value) - {"rules", "max_width_um", "max_height_um"}
    if unknown:
        raise ValueError(f"Unknown project constraints: {', '.join(sorted(unknown))}")

    def number(raw, name):
        if isinstance(raw, bool) or not isinstance(raw, (int, float)) or not math.isfinite(raw) or not 0 < raw <= 100000:
            raise ValueError(f"{name} must be a finite number greater than 0 and at most 100000 µm")
        return float(raw)

    result = {"rules": []}
    for name in ("max_width_um", "max_height_um"):
        if name in value:
            result[name] = number(value[name], name)
    rules = value.get("rules", [])
    if not isinstance(rules, list) or len(rules) > 64:
        raise ValueError("Project rules must be a list of at most 64 rules")
    for index, rule in enumerate(rules):
        if not isinstance(rule, dict):
            raise ValueError(f"Rule {index + 1} must be an object")
        if rule.get("kind") not in ("min_width", "min_space", "min_area"):
            raise ValueError(f"Rule {index + 1}: kind must be min_width, min_space or min_area")
        value_key = "value_um2" if rule["kind"] == "min_area" else "value_um"
        if set(rule) != {"kind", "layer", "datatype", value_key}:
            raise ValueError(f"Rule {index + 1} needs kind, layer, datatype and {value_key}")
        for field in ("layer", "datatype"):
            raw = rule[field]
            if isinstance(raw, bool) or not isinstance(raw, int) or not 0 <= raw <= 65535:
                raise ValueError(f"Rule {index + 1}: {field} must be an integer from 0 to 65535")
        result["rules"].append({**rule, value_key: number(rule[value_key], f"Rule {index + 1} ({value_key})")})
    return result


def check_constraints(layout, top, constraints):
    import klayout.db as db

    constraints = validate_constraints(constraints)
    cell = layout.cell(top)
    box = cell.dbbox()
    markers, missing = [], []
    violations = 0
    checked = 0
    for name, measured in (("max_width_um", box.width()), ("max_height_um", box.height())):
        if name not in constraints:
            continue
        checked += 1
        if measured > constraints[name] + 1e-9:
            violations += 1
            markers.append({"rule": name, "measured_um": measured, "required_um": constraints[name],
                            "bbox": [[box.left, box.bottom], [box.right, box.top]]})
    for rule in constraints["rules"]:
        index = layout.find_layer(rule["layer"], rule["datatype"])
        region = db.Region(cell.begin_shapes_rec(index)).merged() if index is not None else db.Region()
        if region.is_empty():
            missing.append(f"{rule['layer']}/{rule['datatype']}: {rule['kind']}")
            continue
        checked += 1
        if rule["kind"] == "min_area":
            # Polygons are merged before checking; disconnected islands each need the minimum area.
            threshold = math.ceil(rule["value_um2"] / layout.dbu**2 - 1e-9)
            small = region.with_area(None, threshold, False)
            violations += small.size()
            for polygon in small.each():
                if len(markers) >= 1000:
                    break
                bounds = polygon.bbox().to_dtype(layout.dbu)
                markers.append({"rule": "min_area", "layer": f"{rule['layer']}/{rule['datatype']}",
                                "required_um2": rule["value_um2"],
                                "measured_um2": polygon.area() * layout.dbu**2,
                                "bbox": [[bounds.left, bounds.bottom], [bounds.right, bounds.top]]})
            continue
        # Distances are integral DBU. Round a user minimum upward, never weaken it.
        threshold = math.ceil(rule["value_um"] / layout.dbu - 1e-9)
        edges = region.width_check(threshold) if rule["kind"] == "min_width" else region.space_check(threshold)
        violations += edges.size()
        for edge in edges.each():
            if len(markers) >= 1000:
                break
            bounds = edge.bbox().to_dtype(layout.dbu)
            markers.append({"rule": rule["kind"], "layer": f"{rule['layer']}/{rule['datatype']}",
                            "required_um": rule["value_um"],
                            "bbox": [[bounds.left, bounds.bottom], [bounds.right, bounds.top]]})
    result = {"status": "fail" if violations else "not_run" if missing or not checked else "pass",
              "violations": violations, "markers": markers, "checked_rules": checked,
              "missing_layers": missing, "markers_truncated": violations > len(markers)}
    if missing:
        result["reason"] = "No geometry for project rules: " + ", ".join(missing)
    elif not checked:
        result["reason"] = "No project constraints configured"
    return result
