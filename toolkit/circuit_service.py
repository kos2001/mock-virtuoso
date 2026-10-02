"""Circuit endpoints shared by the existing Design Floor."""
from pathlib import Path
import json

from mock_virtuoso.circuit import check_circuit, example, netlist, validate_circuit
from mock_virtuoso.circuit import identifier
from mock_virtuoso.simulation import find_ngspice, simulate

ROOT = Path(__file__).resolve().parents[1]


def catalog():
    from mock_virtuoso.pdk import installed, CORNERS, REVISION
    executable = find_ngspice(ROOT)
    return {"engine": "ngspice", "available": bool(executable and executable.is_file()),
            "example": example(), "analyses": ["op", "dc", "ac", "tran"],
            "components": ["R", "C", "L", "V", "I", "D", "NMOS", "PMOS"],
            "model_profiles": [{"id": "generic", "available": True},
                               {"id": "sky130", "available": installed() is not None, "revision": REVISION}],
            "corners": list(CORNERS),
            "model_scope": "Generic or installed SKY130 1.8 V MOS; public PDK is not foundry certification"}


def experiment(payload):
    from mock_virtuoso.experiments import run_experiment
    return run_experiment(payload, executable=find_ngspice(ROOT), output=ROOT / "simulation-runs")


def postlayout(payload):
    import re
    import hashlib
    from mock_virtuoso.circuit import fields
    fields(payload, ("run_id", "circuit", "ports"), "post-layout testbench")
    run_id = payload.get("run_id", "")
    if not isinstance(run_id, str) or not re.fullmatch(r"[a-f0-9]{32}", run_id):
        raise ValueError("Select a completed verification run")
    directory = (ROOT / "verification-runs" / run_id).resolve()
    if not directory.is_relative_to((ROOT / "verification-runs").resolve()):
        raise ValueError("Invalid verification directory")
    physical = json.loads((directory / "result.json").read_text(encoding="utf-8"))
    if physical.get("pex", {}).get("status") != "pass" or physical.get("lvs", {}).get("status") != "pass":
        raise ValueError("Post-layout simulation requires successful PEX and LVS")
    extracted = physical["pex"]["netlist"]
    # GDS labels are untrusted input even when the netlist was engine generated.
    # A post-layout run must not accept SPICE control/include directives.
    for line in extracted.splitlines():
        line = line.strip()
        if not line or line.startswith("*"):
            continue
        if not re.fullmatch(r"[A-Za-z0-9_./#!$<>\[\]:=+() -]+", line):
            raise ValueError("Unsupported characters in extracted SPICE")
        if not re.match(r"^(?:[XRC][A-Za-z0-9_]*\s|\.subckt\s+extracted\s|\.ends(?:\s+extracted)?$)", line, re.I):
            raise ValueError("Unsafe or unsupported extracted SPICE statement")
    header = re.search(r"^\.subckt\s+extracted\s+([^\n]+)", extracted, re.M | re.I)
    if not header:
        raise ValueError("Extracted top-level port list is missing")
    ports = header[1].split()
    mapping = payload.get("ports")
    if not isinstance(mapping, dict) or set(mapping) != set(ports):
        raise ValueError("Map every extracted port exactly: " + ", ".join(ports))
    nodes = [identifier(mapping[p], "port node", node=True).lower() for p in ports]
    circuit = validate_circuit(payload.get("circuit"))
    circuit["model_profile"] = "sky130"
    if any(d["kind"] not in ("R", "C", "L", "V", "I") for d in circuit["devices"]):
        raise ValueError("Post-layout testbench accepts only sources and RLC loads")
    dut = extracted + "\nX_LAYOUT " + " ".join(nodes) + " extracted\n"
    result = simulate(circuit, executable=find_ngspice(ROOT), output=ROOT / "simulation-runs", extracted_dut=dut)
    result["postlayout"] = {"verification_run_id": run_id, "ports": mapping,
                            "extracted_sha256": hashlib.sha256(extracted.encode()).hexdigest(),
                            "layout_sha256": physical["extraction"]["input_sha256"]}
    if "run_id" in result:
        (ROOT / "simulation-runs" / result["run_id"] / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def inspect(payload):
    circuit = validate_circuit(payload)
    return {"circuit": circuit, "erc": check_circuit(circuit), "netlist": netlist(circuit)}


def run(payload):
    return simulate(payload, executable=find_ngspice(ROOT), output=ROOT / "simulation-runs")


def design_store(client, payload, *, load=False):
    if client is None:
        raise ValueError("Design database is not connected")
    if load:
        if not isinstance(payload, dict) or set(payload) != {"name"}:
            raise ValueError("Load requires a circuit name")
        name = identifier(payload["name"], "name")
    else:
        payload = validate_circuit(payload)
        name = payload["name"]
    prefix = f'let((cv) cv = dbOpenCellViewByType("CIRCUITS" "{name}" "schematic" "schematic" "a") '
    if load:
        skill = prefix + 'mockCircuitRead(cv))'
    else:
        encoded = json.dumps(json.dumps(payload), ensure_ascii=True)
        skill = prefix + f'mockCircuitLoad(cv {encoded}) dbSave(cv))'
    result = client.execute_skill(skill)
    if result.status.value != "success":
        raise ValueError(f"Circuit database operation failed: {result.errors}")
    if load:
        decoded = json.loads(result.output)
        payload = json.loads(decoded) if isinstance(decoded, str) else decoded
    return {"circuit": payload, "library": "CIRCUITS", "view": "schematic"}
