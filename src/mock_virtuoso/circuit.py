"""Declarative circuit connectivity, ERC and portable SPICE generation.

This is a circuit editor model, not an implementation of Cadence's schematic API.
Built-in semiconductor models are explicitly generic, not foundry PDK models.
"""
from __future__ import annotations

import math
import re
from collections import Counter, defaultdict


def number(value, field, low=-1e12, high=1e12):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field}: enter a numeric SI value")
    try:
        value = float(value)
    except OverflowError:
        raise ValueError(f"{field}: out of range") from None
    if not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f"{field}: must be between {low} and {high}")
    return value


def identifier(value, field, *, node=False):
    if node and value == "0":
        return value
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,47}", value):
        raise ValueError(f"{field}: use a simple identifier" + (" or 0 for ground" if node else ""))
    return value


def fields(value, allowed, what):
    if not isinstance(value, dict) or set(value) - set(allowed):
        raise ValueError(f"{what}: expected an object with fields {', '.join(allowed)}")


def validate_circuit(value):
    fields(value, ("name", "devices", "analysis", "temperature_c", "model_profile", "corner"), "circuit")
    from mock_virtuoso.pdk import CORNERS
    profile, corner = value.get("model_profile", "generic"), value.get("corner", "tt")
    if profile not in ("generic", "sky130") or corner not in CORNERS:
        raise ValueError("Invalid model profile or corner")
    devices = value.get("devices")
    if not isinstance(devices, list) or not 1 <= len(devices) <= 128:
        raise ValueError("devices: provide 1–128 components")
    out = {"name": identifier(value.get("name", "CIRCUIT"), "name"), "devices": [],
           "temperature_c": number(value.get("temperature_c", 27), "temperature_c", -100, 250)}
    names = set()
    if "model_profile" in value or "corner" in value:
        out.update(model_profile=profile, corner=corner)
    for i, device in enumerate(devices):
        where = f"devices[{i}]"
        fields(device, ("id", "kind", "nodes", "value", "ac", "pulse", "width", "length"), where)
        kind = device.get("kind")
        if kind not in ("R", "C", "L", "V", "I", "D", "NMOS", "PMOS"):
            raise ValueError(f"{where}: unsupported component kind")
        name = identifier(device.get("id"), where + ".id")
        if name.lower() in names:
            raise ValueError(f"Duplicate component id: {name} (SPICE is case-insensitive)")
        names.add(name.lower())
        nodes = device.get("nodes")
        count = 4 if kind in ("NMOS", "PMOS") else 2
        if not isinstance(nodes, list) or len(nodes) != count:
            raise ValueError(f"{name}: expected {count} nodes" + (" in D,G,S,B order" if count == 4 else ""))
        d = {"id": name, "kind": kind,
             "nodes": [identifier(n, f"{name}.node", node=True).lower() for n in nodes]}
        allowed = {"id", "kind", "nodes"}
        if kind in ("R", "C", "L", "V", "I"):
            allowed.add("value")
            d["value"] = number(device.get("value"), f"{name}.value", 1e-18 if kind in ("R", "C", "L") else -1e12)
        if kind in ("V", "I"):
            allowed.update(("ac", "pulse"))
            d["ac"] = number(device.get("ac", 0), f"{name}.ac", 0)
            if "pulse" in device:
                keys = ("low", "high", "delay", "rise", "fall", "width", "period")
                fields(device["pulse"], keys, f"{name}.pulse")
                d["pulse"] = {k: number(device["pulse"].get(k), f"{name}.pulse.{k}",
                                        -1e12 if k in ("low", "high") else 0) for k in keys}
                if min(d["pulse"][k] for k in ("rise", "fall", "width", "period")) <= 0:
                    raise ValueError(f"{name}: pulse times must be positive")
                if sum(d["pulse"][k] for k in ("rise", "fall", "width")) > d["pulse"]["period"]:
                    raise ValueError(f"{name}: pulse width plus edges exceeds period")
        if count == 4:
            allowed.update(("width", "length"))
            d.update({k: number(device.get(k, 1e-6), f"{name}.{k}", 1e-9, 1) for k in ("width", "length")})
        if set(device) - allowed:
            raise ValueError(f"{name}: parameters not applicable to {kind}: {sorted(set(device) - allowed)}")
        out["devices"].append(d)
    a = value.get("analysis", {"type": "op"})
    fields(a, ("type", "source", "start", "stop", "step", "points"), "analysis")
    kind = a.get("type")
    allowed = {"type"}
    analysis = {"type": kind}
    if kind == "dc":
        allowed.update(("source", "start", "stop", "step"))
        source = identifier(a.get("source"), "analysis.source")
        if not any(d["id"].lower() == source.lower() and d["kind"] in ("V", "I") for d in out["devices"]):
            raise ValueError("DC sweep source must name a voltage or current source")
        analysis.update(source=source, **{k: number(a.get(k), f"analysis.{k}") for k in ("start", "stop", "step")})
        if analysis["step"] == 0 or not 0 < (analysis["stop"] - analysis["start"]) / analysis["step"] <= 10000:
            raise ValueError("DC sweep: step must point toward stop and produce at most 10001 samples")
    elif kind == "tran":
        allowed.update(("step", "stop"))
        analysis.update({k: number(a.get(k), f"analysis.{k}", 1e-15, 1e6) for k in ("step", "stop")})
        if not 1 <= analysis["stop"] / analysis["step"] <= 10000:
            raise ValueError("Transient analysis: stop/step must be between 1 and 10000")
    elif kind == "ac":
        allowed.update(("start", "stop", "points"))
        analysis.update({k: number(a.get(k), f"analysis.{k}", 1e-9, 1e15) for k in ("start", "stop")})
        points = a.get("points", 50)
        if type(points) is not int or not 1 <= points <= 1000 or analysis["stop"] <= analysis["start"]:
            raise ValueError("AC sweep requires 1–1000 points/decade and stop > start")
        if math.log10(analysis["stop"] / analysis["start"]) * points > 10000:
            raise ValueError("AC sweep exceeds 10000 samples")
        analysis["points"] = points
    elif kind != "op":
        raise ValueError("analysis.type must be op, dc, ac or tran")
    if set(a) - allowed:
        raise ValueError("Analysis contains parameters for a different analysis type")
    out["analysis"] = analysis
    return out


def check_circuit(value):
    circuit = validate_circuit(value)
    issues = []
    graph = defaultdict(set)
    counts = Counter(n for d in circuit["devices"] for n in d["nodes"])
    def issue(code, message, **context):
        issues.append({"severity": "error", "code": code, "message": message, **context})
    if "0" not in counts:
        issue("ERC-GROUND", "Circuit has no reference ground (node 0)")
    ideal = {}
    def root(n):
        ideal.setdefault(n, n)
        while ideal[n] != n:
            n = ideal[n]
        return n
    for d in circuit["devices"]:
        nodes, kind = d["nodes"], d["kind"]
        if len(nodes) == 2 and nodes[0] == nodes[1]:
            issue("ERC-SHORT", "Component terminals share the same net", device=d["id"])
        if kind in ("V", "L"):
            a, b = map(root, nodes)
            if a == b:
                issue("ERC-IDEAL-LOOP", "Loop of ideal voltage sources/inductors has no unique branch current", device=d["id"])
            ideal[a] = b
        # DC path screen: capacitors and ideal current sources do not anchor a net.
        if kind not in ("C", "I"):
            connected = [nodes[0], nodes[2], nodes[3]] if len(nodes) == 4 else nodes
            for a in connected:
                graph[a].update(connected)
    reached, pending = set(), ["0"]
    while pending:
        n = pending.pop()
        if n not in reached:
            reached.add(n)
            pending.extend(graph[n] - reached)
    for n, count in sorted(counts.items()):
        if n not in reached:
            issue("ERC-FLOATING", "No structural DC path to ground; check bias connectivity", net=n)
        if count == 1 and n != "0":
            issue("ERC-DANGLING", "Net has only one component terminal", net=n)
    if circuit["analysis"]["type"] == "ac" and not any(d.get("ac", 0) for d in circuit["devices"]):
        issue("ERC-AC-SOURCE", "AC analysis needs a source with nonzero AC amplitude")
    return {"status": "fail" if issues else "pass", "issues": issues, "nodes": sorted(counts),
            "scope": "Structural circuit ERC; semiconductor operating regions and foundry ERC are not checked"}


def netlist(value):
    c = validate_circuit(value)
    pdk = c.get("model_profile") == "sky130"
    lines = [f"* {c['name']} — generic circuit, not a foundry-qualified model".replace("—", "-"),
             f".temp {c['temperature_c']:.12g}"]
    for d in c["devices"]:
        kind = d["kind"]
        prefix = "M" if kind in ("NMOS", "PMOS") else kind
        if pdk and kind in ("NMOS", "PMOS"):
            prefix = "X"
        line = f"{prefix}_{d['id']} " + " ".join(d["nodes"])
        if kind in ("R", "C", "L"):
            line += f" {d['value']:.12g}"
        elif kind in ("V", "I"):
            line += f" DC {d['value']:.12g} AC {d['ac']:.12g}"
            if "pulse" in d:
                line += " PULSE(" + " ".join(f"{v:.12g}" for v in d["pulse"].values()) + ")"
        elif kind == "D":
            if pdk:
                raise ValueError("SKY130 profile currently supports 1.8 V NMOS/PMOS; generic diode is not a PDK device")
            line += " DEMO_D"
        else:
            if pdk:
                model = "nfet" if kind == "NMOS" else "pfet"
                line += f" sky130_fd_pr__{model}_01v8 W={d['width'] * 1e6:.12g} L={d['length'] * 1e6:.12g}"
            else:
                line += f" DEMO_{kind} W={d['width']:.12g} L={d['length']:.12g}"
        lines.append(line)
    lines += [".model DEMO_D D(IS=1e-14 N=1)",
              ".model DEMO_NMOS NMOS(LEVEL=1 VTO=0.7 KP=100u LAMBDA=0.02)",
              ".model DEMO_PMOS PMOS(LEVEL=1 VTO=-0.7 KP=50u LAMBDA=0.02)"]
    if pdk:
        lines[0] = f"* {c['name']} - SKY130 {c.get('corner', 'tt')} (public PDK)"
        lines.insert(1, '.include "models.spice"')
    a = c["analysis"]
    if a["type"] == "op":
        lines.append(".op")
    elif a["type"] == "dc":
        d = next(d for d in c["devices"] if d["id"].lower() == a["source"].lower())
        lines.append(f".dc {d['kind']}_{d['id']} {a['start']:.12g} {a['stop']:.12g} {a['step']:.12g}")
    elif a["type"] == "tran":
        lines.append(f".tran {a['step']:.12g} {a['stop']:.12g}")
    else:
        lines.append(f".ac dec {a['points']} {a['start']:.12g} {a['stop']:.12g}")
    return "\n".join(lines + [".end", ""])


def example():
    return {"name": "DIVIDER", "devices": [
        {"id": "V1", "kind": "V", "nodes": ["vin", "0"], "value": 1, "ac": 1},
        {"id": "R1", "kind": "R", "nodes": ["vin", "vout"], "value": 1000},
        {"id": "R2", "kind": "R", "nodes": ["vout", "0"], "value": 1000}],
        "analysis": {"type": "op"}, "temperature_c": 27}
