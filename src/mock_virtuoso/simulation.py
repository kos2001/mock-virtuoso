"""Real ngspice batch runs for validated declarative circuits."""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import time
import uuid

from mock_virtuoso.circuit import check_circuit, netlist, validate_circuit


def find_ngspice(root=None):
    configured = os.environ.get("NGSPICE_EXE") or shutil.which("ngspice")
    if configured:
        return Path(configured).resolve()
    root = Path(root or Path.cwd())
    found = sorted((root / ".tools" / "ngspice").rglob("ngspice_con.exe"))
    if not found:
        found = sorted((root / ".tools" / "ngspice").rglob("ngspice.exe"))
    return found[0].resolve() if found else None


def read_raw(path, *, full=False):
    """Read ngspice ASCII raw data, preserving complex AC components."""
    if path.stat().st_size > 64 * 1024 * 1024:
        raise ValueError("Simulation output exceeds 64 MiB")
    variables = []
    # splitlines handles both CRLF and LF files from the Windows console build.
    content = path.read_text(encoding="utf-8", errors="replace").splitlines()
    vpos = content.index("Variables:")
    dpos = content.index("Values:")
    for line in content[vpos + 1:dpos]:
        index, name, unit = line.split()[:3]
        if int(index) != len(variables):
            raise ValueError("Invalid simulation variable index")
        variables.append({"name": name, "unit": unit})
    count = int(next(line.split(":", 1)[1] for line in content[:vpos] if line.startswith("No. Points:")))
    if not variables or not 0 < count <= 100000:
        raise ValueError("Simulation returned no samples or too many samples")
    complex_data = any(line.startswith("Flags:") and "complex" in line for line in content[:vpos])
    values = [line.strip() for line in content[dpos + 1:] if line.strip()]
    if len(values) != count * len(variables):
        raise ValueError("Incomplete simulation output")
    stride = 1 if full else max(1, math.ceil(count / 2000))
    indices = sorted(set(range(0, count, stride)) | {count - 1})
    columns = [{**v, "real": [], "imag": []} for v in variables]
    for row in indices:
        for col in range(len(variables)):
            value = values[row * len(variables) + col]
            if col == 0:
                index, value = value.split(None, 1)
                if int(index) != row:
                    raise ValueError("Invalid simulation sample index")
            pair = value.split(",") if complex_data else [value, "0"]
            real, imag = map(float, pair)
            if not math.isfinite(real) or not math.isfinite(imag):
                raise ValueError("Non-finite simulation result")
            columns[col]["real"].append(real)
            columns[col]["imag"].append(imag)
    return {"plot": next(line.split(":", 1)[1].strip() for line in content if line.startswith("Plotname:")),
            "sample_count": count, "returned_samples": len(indices), "complex": complex_data,
            "columns": columns}


def simulate(value, *, executable=None, output="simulation-runs", timeout=30, extracted_dut=None):
    circuit = validate_circuit(value)
    erc = check_circuit(circuit)
    spice = netlist(circuit)
    if extracted_dut is not None:
        # Internal adapter only: the HTTP service resolves a completed extraction,
        # never an uploaded SPICE program. Structural ERC cannot see this subcircuit.
        erc = {"status": "not_run", "issues": [], "scope": "Post-layout connectivity uses extracted subcircuit; structural circuit ERC is not applicable"}
        spice = spice.rsplit(".end", 1)[0] + extracted_dut + "\n.end\n"
    if erc["status"] == "fail":
        return {"status": "blocked", "erc": erc, "netlist": spice,
                "reason": "Resolve circuit ERC errors before simulation"}
    executable = Path(executable).resolve() if executable else find_ngspice()
    if executable is None or not executable.is_file():
        return {"status": "not_run", "erc": erc, "netlist": spice,
                "reason": "Install ngspice and set NGSPICE_EXE"}
    run_id = uuid.uuid4().hex
    directory = Path(output).resolve() / run_id
    directory.mkdir(parents=True)
    (directory / "circuit.json").write_text(json.dumps(circuit, indent=2), encoding="utf-8")
    (directory / "input.cir").write_text(spice, encoding="ascii")
    started = time.monotonic()
    result = {"run_id": run_id, "status": "error", "engine": "ngspice", "erc": erc,
              "analysis": circuit["analysis"],
              "netlist": spice, "input_sha256": hashlib.sha256(spice.encode()).hexdigest(),
              "model_scope": "Generic RLC/sources, diode and level-1 MOS; not foundry PDK models"}
    if circuit.get("model_profile") == "sky130":
        from mock_virtuoso.pdk import models
        try:
            model_text, result["pdk"] = models(circuit.get("corner", "tt"))
            (directory / "models.spice").write_text(model_text, encoding="utf-8")
            result["model_scope"] = "SKY130 1.8 V MOS models; ideal RLC and sources"
        except (OSError, ValueError) as exc:
            result.update(status="not_run", reason=f"PDK model loading failed: {exc}")
            (directory / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
            return result
    env = {**os.environ, "SPICE_ASCIIRAWFILE": "1"}
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    try:
        version = subprocess.run([str(executable), "-v"], capture_output=True, timeout=5,
                                 encoding="utf-8", errors="replace", creationflags=flags)
        result["engine_version"] = version.stdout.strip()[:2000]
        with (directory / "process.log").open("w", encoding="utf-8") as log:
            completed = subprocess.run([str(executable), "-n", "-b", "-r", "result.raw", "input.cir"],
                                       cwd=directory, env=env, stdout=log, stderr=subprocess.STDOUT,
                                       timeout=timeout, creationflags=flags)
        result["exit_code"] = completed.returncode
        result["log"] = (directory / "process.log").read_text(encoding="utf-8", errors="replace")[-24000:]
        if completed.returncode != 0:
            result["reason"] = "ngspice failed; inspect the simulation log"
        else:
            result["data"] = read_raw(directory / "result.raw")
            result["status"] = "pass"
    except subprocess.TimeoutExpired:
        result["reason"] = f"Simulation timed out after at most {timeout} seconds"
    except (OSError, ValueError, IndexError, StopIteration) as exc:
        result["reason"] = f"Simulation output error: {exc}"
    result["elapsed_s"] = round(time.monotonic() - started, 3)
    (directory / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result
