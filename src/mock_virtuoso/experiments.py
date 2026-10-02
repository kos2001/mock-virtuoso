"""Bounded testbench/corner/temperature/source sweeps and measured acceptance."""
from copy import deepcopy
from datetime import datetime, timezone
from itertools import product
import json
import math
from pathlib import Path
import uuid

from mock_virtuoso.circuit import fields, identifier, netlist, number, validate_circuit
from mock_virtuoso.pdk import CORNERS
from mock_virtuoso.simulation import read_raw, simulate


def validate_plan(value):
    fields(value, ("name", "circuit", "corners", "temperatures", "sweep", "measurements"), "experiment")
    circuit = validate_circuit(value.get("circuit"))
    netlist(circuit)
    corners = value.get("corners", [circuit.get("corner", "tt")])
    temps = value.get("temperatures", [circuit["temperature_c"]])
    if not isinstance(corners, list) or not corners or any(c not in CORNERS for c in corners):
        raise ValueError("Choose at least one supported corner")
    if circuit.get("model_profile", "generic") == "generic" and corners != ["tt"]:
        raise ValueError("Process corners require a PDK model profile")
    if not isinstance(temps, list) or not temps:
        raise ValueError("Choose at least one temperature")
    temps = [number(t, "temperature", -100, 250) for t in temps]
    sweep = value.get("sweep")
    if sweep is not None:
        fields(sweep, ("device", "values"), "sweep")
        device = next((d for d in circuit["devices"] if d["id"] == sweep.get("device")), None)
        if device is None or device["kind"] not in ("V", "I", "R", "C", "L"):
            raise ValueError("Sweep requires an existing source or RLC device")
        if not isinstance(sweep.get("values"), list) or not sweep["values"]:
            raise ValueError("Supply sweep values")
        for v in sweep["values"]:
            changed = deepcopy(circuit)
            next(d for d in changed["devices"] if d["id"] == device["id"])["value"] = v
            validate_circuit(changed)
    count = len(corners) * len(temps) * (len(sweep["values"]) if sweep else 1)
    if count > 30:
        raise ValueError("An experiment is limited to 30 runs")
    measurements = value.get("measurements", [])
    if not isinstance(measurements, list) or not 1 <= len(measurements) <= 16:
        raise ValueError("Provide 1–16 acceptance measurements")
    names = set()
    for m in measurements:
        fields(m, ("name", "signal", "statistic", "component", "min", "max"), "measurement")
        name = identifier(m.get("name"), "measurement name")
        if name in names:
            raise ValueError("Duplicate measurement name")
        names.add(name)
        if not isinstance(m.get("signal"), str) or len(m["signal"]) > 128:
            raise ValueError("Measurement signal required")
        if m.get("statistic", "last") not in ("last", "min", "max", "mean") or m.get("component", "real") not in ("real", "magnitude"):
            raise ValueError("Unsupported measurement")
        if "min" not in m and "max" not in m:
            raise ValueError("Measurement requires a min or max acceptance bound")
        for bound in ("min", "max"):
            if bound in m:
                number(m[bound], bound)
        if m.get("min", -math.inf) > m.get("max", math.inf):
            raise ValueError("Measurement min exceeds max")
    return {"name": identifier(value.get("name", "EXPERIMENT"), "experiment name"),
            "circuit": circuit, "corners": corners, "temperatures": temps,
            "sweep": sweep, "measurements": measurements}


def measure(data, specifications):
    results = []
    for m in specifications:
        column = next((c for c in data["columns"] if c["name"].lower() == m["signal"].lower()), None)
        if column is None:
            results.append({**m, "status": "error", "reason": "Signal not present in simulation output"})
            continue
        values = column["real"] if m.get("component", "real") == "real" else [math.hypot(r, i) for r, i in zip(column["real"], column["imag"])]
        statistic = m.get("statistic", "last")
        value = {"last": lambda: values[-1], "min": lambda: min(values),
                 "max": lambda: max(values), "mean": lambda: math.fsum(values) / len(values)}[statistic]()
        passed = m.get("min", -math.inf) <= value <= m.get("max", math.inf)
        results.append({**m, "value": value, "unit": column["unit"], "status": "pass" if passed else "fail"})
    return results


def run_experiment(value, *, executable=None, output="simulation-runs"):
    plan = validate_plan(value)
    output = Path(output).resolve()
    directory = output / ("experiment-" + uuid.uuid4().hex)
    directory.mkdir(parents=True)
    report = {"run_id": directory.name, "created_at": datetime.now(timezone.utc).isoformat(),
              "plan": plan, "runs": [], "status": "running", "foundry_qualified": False}
    def save():
        (directory / "result.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    save()
    sweep = plan["sweep"]
    for corner, temperature, v in product(plan["corners"], plan["temperatures"], sweep["values"] if sweep else [None]):
        circuit = deepcopy(plan["circuit"])
        circuit.update(corner=corner, temperature_c=temperature)
        if sweep:
            next(d for d in circuit["devices"] if d["id"] == sweep["device"])["value"] = v
        result = simulate(circuit, executable=executable, output=directory)
        measurements = []
        if result["status"] == "pass":
            try:
                measurements = measure(read_raw(directory / result["run_id"] / "result.raw", full=True), plan["measurements"])
            except (OSError, ValueError, IndexError, StopIteration, OverflowError) as exc:
                measurements = [{"status": "error", "reason": f"Cannot measure complete raw output: {exc}"}]
        status = "pass" if result["status"] == "pass" and all(m["status"] == "pass" for m in measurements) else "fail"
        report["runs"].append({"corner": corner, "temperature_c": temperature, "sweep_value": v,
                               "status": status, "measurements": measurements, "simulation": result})
        save()
    report["status"] = "pass" if all(r["status"] == "pass" for r in report["runs"]) else "fail"
    save()
    return report


def history(output):
    results = []
    paths = sorted(Path(output).glob("experiment-*/result.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:30]
    for path in paths:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            results.append({"run_id": value["run_id"], "name": value["plan"]["name"],
                            "created_at": value["created_at"], "status": value["status"], "runs": len(value["runs"])})
        except (OSError, ValueError, KeyError):
            continue
    return results
