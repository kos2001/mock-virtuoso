"""Local floor adapter for uploaded GDS/SPICE verification jobs."""
import base64
import binascii
import os
from pathlib import Path
import shutil
import tempfile

from mock_virtuoso.verification import run_verification
from mock_virtuoso.project_rules import validate_constraints

ROOT = Path(__file__).resolve().parents[1]


def find_klayout():
    configured = os.environ.get("KLAYOUT_EXE") or shutil.which("klayout")
    if configured:
        return configured
    local = ROOT / ".tools" / "klayout"
    for pattern in ("klayout_app.exe", "klayout.exe", "klayout.app/Contents/MacOS/klayout"):
        binaries = sorted(path for path in local.rglob(pattern) if path.is_file())
        if binaries:
            return str(binaries[0])
    for directory in (Path("/Applications"), Path.home() / "Applications"):
        binary = directory / "klayout.app" / "Contents" / "MacOS" / "klayout"
        if binary.is_file():
            return str(binary)
    return None


def validate_settings(payload):
    if not isinstance(payload, dict):
        raise ValueError("Project settings must be an object")
    allowed = {"schema_version", "pdk", "top", "scope", "substrate", "spice_units", "project_constraints", "physical_checks"}
    if set(payload) - allowed:
        raise ValueError("Unknown project settings: " + ", ".join(sorted(set(payload) - allowed)))
    if type(payload.get("schema_version", 1)) is not int or payload.get("schema_version", 1) != 1:
        raise ValueError("Unsupported project settings version")
    if payload.get("pdk", "sky130") != "sky130":
        raise ValueError("Only the installed SKY130 deck profile is supported")
    scope = payload.get("scope", "cell")
    units = payload.get("spice_units", "micron")
    substrate = payload.get("substrate", "sky130_gnd")
    top = payload.get("top", "")
    if scope not in ("cell", "chip") or units not in ("micron", "si"):
        raise ValueError("Invalid review scope or SPICE units")
    if not isinstance(substrate, str) or not substrate.strip() or len(substrate) > 256:
        raise ValueError("Enter a substrate net name of at most 256 characters")
    if not isinstance(top, str) or len(top) > 256:
        raise ValueError("Top cell name must be text of at most 256 characters")
    if type(payload.get("physical_checks", False)) is not bool:
        raise ValueError("physical_checks must be boolean")
    return {**({"physical_checks": payload["physical_checks"]} if "physical_checks" in payload else {}),
            "schema_version": 1, "pdk": "sky130", "top": top.strip(), "scope": scope,
            "substrate": substrate.strip(), "spice_units": units,
            "project_constraints": validate_constraints(payload.get("project_constraints"))}


def catalog():
    decks = Path(os.environ.get("SKY130_DECKS", str(ROOT / ".tools" / "sky130")))
    return {"pdks": [{"id": "sky130", "name": "SKY130 · 공개 PDK",
                       "checks": {name: (decks / file).is_file() for name, file in
                                  (("drc", "sky130.drc"), ("lvs", "sky130.lvs"), ("density", "density.lydrc"))},
                       "defaults": validate_settings({}),
                       "layers": [{"name": name, "layer": layer, "datatype": 20}
                                  for name, layer in (("nwell", 64), ("diff", 65), ("poly", 66),
                                                      ("li1", 67), ("met1", 68), ("met2", 69),
                                                      ("met3", 70), ("met4", 71), ("met5", 72))]}]}


def decode_layout(payload):
    if not isinstance(payload, dict) or not isinstance(payload.get("gds_base64"), str):
        raise ValueError("Select a GDS file")
    try:
        data = base64.b64decode(payload["gds_base64"], validate=True)
    except (ValueError, binascii.Error) as exc:
        raise ValueError("Invalid GDS upload encoding") from exc
    if not data or len(data) > 20 * 1024 * 1024:
        raise ValueError("GDS file must be between 1 byte and 20 MiB")
    return data


def inspect_upload(payload):
    import klayout.db as db
    data = decode_layout(payload)
    output = ROOT / "verification-runs"
    output.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output, prefix="inspect-") as temporary:
        path = Path(temporary) / "input.gds"
        path.write_bytes(data)
        layout = db.Layout()
        layout.read(str(path))
        cells = []
        for cell in layout.top_cells():
            box = cell.dbbox()
            cells.append({"name": cell.name, "width_um": box.width(), "height_um": box.height()})
        names = {p["layer"]: p["name"] for p in catalog()["pdks"][0]["layers"]}
        return {"dbu_um": layout.dbu, "top_cells": cells,
                "layers": [{"layer": info.layer, "datatype": info.datatype,
                            "name": names.get(info.layer, "") if info.datatype == 20 else ""}
                           for info in layout.layer_infos()]}


def verify_upload(payload):
    if not isinstance(payload, dict):
        raise ValueError("Expected a JSON object")
    settings = validate_settings({key: value for key, value in payload.items()
                                  if key not in ("gds_base64", "netlist")})
    top = settings["top"]
    if not isinstance(top, str) or not top.strip() or len(top) > 256:
        raise ValueError("Enter the exact GDS top cell name")
    data = decode_layout(payload)
    spice = payload.get("netlist")
    if spice is not None and (not isinstance(spice, str) or len(spice) > 2 * 1024 * 1024):
        raise ValueError("SPICE netlist must be text of at most 2 MiB")
    executable = find_klayout()
    if not executable:
        raise ValueError("KLayout executable not found; install KLayout and set KLAYOUT_EXE")
    decks = Path(os.environ.get("SKY130_DECKS", str(ROOT / ".tools" / "sky130")))
    output = ROOT / "verification-runs"
    output.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output, prefix="upload-") as temporary:
        source = Path(temporary) / "input.gds"
        source.write_bytes(data)
        reference = None
        if spice is not None:
            reference = Path(temporary) / "reference.spice"
            reference.write_text(spice, encoding="utf-8")
        return run_verification(executable=executable, gds=source, top=top.strip(),
                                decks=decks, output=output, netlist=reference,
                                substrate=settings["substrate"], scope=settings["scope"],
                                spice_units=settings["spice_units"],
                                project_constraints=settings["project_constraints"],
                                physical_checks=settings.get("physical_checks", False))


def evidence(run_id):
    """Bundle one immutable run's inputs, decks, logs and result for external review."""
    import io
    import json
    import re
    import zipfile
    if not re.fullmatch(r"[a-f0-9]{32}", run_id):
        raise ValueError("Invalid verification run id")
    directory = (ROOT / "verification-runs" / run_id).resolve()
    if not directory.is_relative_to((ROOT / "verification-runs").resolve()):
        raise ValueError("Invalid evidence directory")
    result = json.loads((directory / "result.json").read_text(encoding="utf-8"))
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in directory.rglob("*"):
            if path.is_file() and not path.is_symlink() and path.resolve().is_relative_to(directory):
                archive.write(path, path.relative_to(directory).as_posix())
        archive.writestr("REVIEW.json", json.dumps({"run_id": run_id, "foundry_qualified": False,
            "signoff": result["signoff"], "required_external_evidence": [
                "Foundry-accepted tool/deck versions and process agreement",
                "Project electrical, timing, reliability and extraction checks",
                "Reviewer approval and approved waivers"]}, indent=2))
    return buffer.getvalue()
