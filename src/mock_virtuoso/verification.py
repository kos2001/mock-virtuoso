"""Run real KLayout SKY130 decks against GDS and reference SPICE files.

Deck results are physical-verification evidence, not a tapeout authorization.
This module deliberately does not remap mockTech geometry into a real PDK.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path


def fingerprint(path):
    path = Path(path)
    return {"path": str(path.resolve()),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def read_drc(path):
    import klayout.rdb as rdb

    report = rdb.ReportDatabase()
    report.load(str(path))
    markers = []
    for item in report.each_item():
        if len(markers) == 1000:
            break
        markers.append({"category": report.category_by_id(item.category_id()).name(),
                        "cell": report.cell_by_id(item.cell_id()).name(),
                        "values": [v.to_s() for v in item.each_value()]})
    return {"status": "fail" if report.num_items() else "pass",
            "violations": report.num_items(), "markers": markers,
            "markers_truncated": report.num_items() > len(markers)}


def read_lvs(path):
    import klayout.db as db

    report = db.LayoutVsSchematic()
    report.read(str(path))
    xref = report.xref()
    circuits = []
    extracted = report.netlist()
    devices = sum(1 for c in extracted.each_circuit() for _ in c.each_device()) if extracted else 0
    if xref is not None:
        for pair in xref.each_circuit_pair():
            circuits.append({"layout": pair.first().name if pair.first() else None,
                             "schematic": pair.second().name if pair.second() else None,
                             "status": str(pair.status())})
    # An empty cross reference is an absent comparison, never a clean LVS.
    status = "pass" if devices and circuits and all(c["status"] == "Match" for c in circuits) else "fail"
    result = {"status": status, "circuits": circuits, "extracted_devices": devices}
    if not devices:
        result["reason"] = "No devices extracted; an empty circuit match is not accepted"
    return result


def signoff_status(result, scope):
    """An actionable review gate, separate from foundry authorization."""
    required = ["drc", "lvs"] if scope == "cell" else ["drc", "lvs", "density", "erc", "antenna"]
    if result.get("extraction"):
        required += [k for k in ("pex", "antenna") if k not in required]
    if result.get("project_constraints") and result["project_constraints"] != {"rules": []}:
        required.append("project_rules")
    checklist = []
    for name in required:
        check = result.get(name, {"status": "not_run", "reason": "No qualified backend configured"})
        checklist.append({"check": name, "status": check["status"],
                          "reason": check.get("reason", "")})
    blocking = [c["check"] for c in checklist if c["status"] != "pass"]
    return {"scope": scope, "status": "blocked" if blocking else "ready_for_review",
            "eligible": False, "blocking_checks": blocking, "checklist": checklist,
            "reason": "Review readiness is not foundry sign-off certification. Project-specific electrical, timing, reliability and extraction requirements remain subject to review."}


def run_verification(*, executable, gds, top, decks, output, netlist=None, timeout=300,
                     substrate="sky130_gnd", scope="cell", spice_units="micron",
                     project_constraints=None, physical_checks=False):
    """Create an isolated run directory; return a JSON-serializable report.

    Paths and deck selection are local operator configuration. No shell is used.
    Inputs are snapshotted so later edits cannot rewrite a run's evidence.
    """
    import klayout.db as db
    from mock_virtuoso.project_rules import validate_constraints, check_constraints

    project_constraints = validate_constraints(project_constraints)

    if timeout <= 0:
        raise ValueError("timeout must be positive")
    if scope not in ("cell", "chip"):
        raise ValueError("scope must be cell or chip")
    if spice_units not in ("micron", "si"):
        raise ValueError("spice_units must be micron or si")
    executable = str(Path(shutil.which(str(executable)) or executable).resolve())
    if not isinstance(substrate, str) or not substrate or len(substrate) > 256:
        raise ValueError("substrate net name must be a nonempty string of at most 256 characters")
    gds, decks = Path(gds).resolve(), Path(decks).resolve()
    netlist = Path(netlist).resolve() if netlist else None
    layout = db.Layout()
    layout.read(str(gds))
    cell = layout.cell(top)
    if cell is None or cell.is_empty():
        raise ValueError("top cell is missing or empty")
    if netlist is not None and not netlist.is_file():
        raise ValueError("reference netlist does not exist")
    for name in ("sky130.drc", "sky130.lvs"):
        if not (decks / name).is_file():
            raise ValueError(f"missing rule deck: {decks / name}")
    run_id = uuid.uuid4().hex
    work = Path(output).resolve() / run_id
    work.mkdir(parents=True)
    manifest = {"gds": fingerprint(gds),
                "drc_deck": fingerprint(decks / "sky130.drc"),
                "lvs_deck": fingerprint(decks / "sky130.lvs")}
    # Preserve the exact GDS format suffix (OASIS inputs are accepted by KLayout).
    input_copy = work / ("input" + gds.suffix)
    input_copy.write_bytes(gds.read_bytes())
    for name in ("sky130.drc", "sky130.lvs"):
        (work / name).write_bytes((decks / name).read_bytes())
    if (decks / "density.lydrc").is_file():
        (work / "density.lydrc").write_bytes((decks / "density.lydrc").read_bytes())
        manifest["density_deck"] = fingerprint(work / "density.lydrc")
    if netlist:
        manifest["netlist"] = fingerprint(netlist)
        # Relative include semantics cannot survive a standalone snapshot.
        # Refuse instead of comparing against a silently incomplete schematic.
        spice = netlist.read_text(encoding="utf-8")
        if any(re.match(r"\s*\.(?:inc(?:lude)?|lib)\b", line, re.IGNORECASE)
               for line in spice.splitlines()):
            raise ValueError("provide a self-contained SPICE netlist (no .include/.lib)")
        (work / "reference.spice").write_text(spice, encoding="utf-8")
    # Hash the preserved files, which are the actual engine inputs.
    snapshots = {"gds": input_copy, "drc_deck": work / "sky130.drc",
                 "lvs_deck": work / "sky130.lvs"}
    if netlist:
        snapshots["netlist"] = work / "reference.spice"
    for name, snapshot in snapshots.items():
        manifest[name].update(sha256=fingerprint(snapshot)["sha256"], snapshot=str(snapshot))
    layout = db.Layout()
    layout.read(str(input_copy))
    cell = layout.cell(top)
    if cell is None or cell.is_empty():
        raise ValueError("snapshotted top cell is missing or empty")
    result = {"schema_version": 1, "run_id": run_id,
              "created_at": datetime.now(timezone.utc).isoformat(),
              "engine": "KLayout", "technology": "SKY130", "top": top,
              "inputs": manifest, "directory": str(work),
              "signoff": {"status": "not_qualified", "eligible": False,
                          "reason": "Open-source DRC/LVS checks alone do not establish foundry sign-off; ERC, antenna, density and project-required checks must also be qualified."}}
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    environment = os.environ.copy()
    # The Windows distribution decodes an absolute Korean installation path
    # incorrectly while initializing its embedded Python. Relative paths avoid
    # that conversion without changing the machine locale or installation.
    python_root = Path(executable).parent
    if os.name == "nt" and (python_root / "lib/python3.11").is_dir():
        try:
            relative = os.path.relpath(python_root, work)
        except ValueError:  # Separate Windows drives.
            relative = str(python_root)
        environment.setdefault("KLAYOUT_PYTHONHOME", relative)
        environment.setdefault("KLAYOUT_PYTHONPATH", ";".join(
            str(Path(relative) / suffix) for suffix in
            ("lib/python3.11", "lib/python3.11/lib-dynload", "lib/python3.11/site-packages")))
    try:
        version = subprocess.run([str(executable), "-v"], capture_output=True,
                                 text=True, timeout=30, creationflags=flags,
                                 cwd=work, env=environment)
    except subprocess.TimeoutExpired as exc:
        raise ValueError("KLayout version probe timed out") from exc
    result["engine_version"] = (version.stdout + version.stderr).strip()
    for kind in ("drc", "lvs", "density"):
        if kind == "lvs" and netlist is None:
            result[kind] = {"status": "not_run", "reason": "Reference SPICE netlist required"}
            continue
        if kind == "density":
            boundary = layout.find_layer(235, 4)
            if scope != "chip":
                result[kind] = {"status": "not_run", "reason": "Chip-level density is outside the cell review scope"}
                continue
            if boundary is None or db.Region(cell.begin_shapes_rec(boundary)).area() <= 0:
                result[kind] = {"status": "not_run", "reason": "Density requires a nonempty chip boundary on GDS 235/4"}
                continue
            if not (work / "density.lydrc").is_file():
                result[kind] = {"status": "not_run", "reason": "Download the pinned density deck first"}
                continue
        report_file = work / ("lvs.lvsdb" if kind == "lvs" else f"{kind}.lyrdb")
        params = {"input": str(input_copy), "top_cell": top, "report": str(report_file)}
        if kind == "drc":
            # Upstream defaults disable these groups. Never rely on them.
            params.update(feol="true", beol="true", offgrid="true", floating_met="true")
        elif kind == "lvs":
            params["schematic"] = str(work / "reference.spice")
            params["target_netlist"] = str(work / "extracted.spice")
            params["convert_subckts"] = "true"
            params["lvs_sub"] = substrate
            params["scale"] = "true" if spice_units == "micron" else "false"
        deck_file = "density.lydrc" if kind == "density" else f"sky130.{kind}"
        command = [str(executable), "-b", "-r", str(work / deck_file)]
        for key, value in params.items():
            command.extend(["-rd", f"{key}={value}"])
        log = work / f"{kind}.log"
        try:
            with log.open("w", encoding="utf-8") as stream:
                proc = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT,
                                      cwd=work, timeout=timeout, creationflags=flags,
                                      env=environment)
            if not report_file.is_file():
                check = {"status": "error", "reason": "Engine produced no result database"}
            else:
                check = (read_lvs if kind == "lvs" else read_drc)(report_file)
                # Nonzero exit may mean LVS mismatch, but never a passing check.
                if proc.returncode and check["status"] != "fail":
                    check.update(status="error", reason="Engine exited unsuccessfully")
            check["exit_code"] = proc.returncode
        except subprocess.TimeoutExpired:
            check = {"status": "error", "reason": f"Engine timed out after {timeout}s"}
        except (OSError, RuntimeError, ValueError) as exc:
            check = {"status": "error", "reason": str(exc)}
        result[kind] = {**check, "log": str(log), "report": str(report_file),
                        "parameters": params}
    result["drc_lvs_passed"] = all(result[k]["status"] == "pass" for k in ("drc", "lvs"))
    result["project_constraints"] = project_constraints
    result["project_rules"] = check_constraints(layout, top, project_constraints)
    result["settings"] = {"schema_version": 1, "pdk": "sky130", "top": top,
                          "scope": scope, "substrate": substrate, "spice_units": spice_units,
                          "project_constraints": project_constraints}
    (work / "settings.json").write_text(json.dumps(result["settings"], indent=2), encoding="utf-8")
    if physical_checks:
        from mock_virtuoso.extraction import extract
        result["extraction"] = extract(input_copy, top, output=work)
        result.update({k: result["extraction"][k] for k in ("pex", "antenna")})
        result["settings"]["physical_checks"] = True
        (work / "settings.json").write_text(json.dumps(result["settings"], indent=2), encoding="utf-8")
    result["signoff"] = signoff_status(result, scope)
    result["checks_passed"] = result["signoff"]["status"] == "ready_for_review"
    (work / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result
