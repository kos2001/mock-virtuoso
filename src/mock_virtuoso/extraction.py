"""Magic SKY130 RC extraction and antenna checks, with native artifacts."""
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import uuid

from mock_virtuoso.pdk import ROOT, installed, revision


def linux_path(path):
    p = Path(path).resolve().as_posix()
    return "/mnt/" + p[0].lower() + p[2:] if len(p) > 2 and p[1] == ":" else p


def tcl(value):
    return "[encoding convertfrom utf-8 [binary decode base64 {" + base64.b64encode(str(value).encode()).decode() + "}]]"


def magic_binary():
    local = ROOT / ".tools/magic-install/bin/magic"
    return local if local.is_file() else None


def extract(gds, top, *, output="verification-runs", timeout=120):
    pdk, binary = installed(), magic_binary()
    if not pdk or not binary:
        return {k: {"status": "not_run", "reason": "Install Magic and SKY130 technology"} for k in ("pex", "antenna")}
    directory = Path(output).resolve() / ("magic-" + uuid.uuid4().hex)
    directory.mkdir(parents=True)
    shutil.copyfile(gds, directory / "input.gds")
    tech = pdk / "libs.tech/magic/sky130A.tech"
    shutil.copyfile(tech, directory / "sky130A.tech")
    # Tcl catches errors explicitly: Magic itself may otherwise exit with status 0.
    script = """drc off
gds readonly true
gds read input.gds
load TOP
select top cell
flatten extracted
load extracted
select top cell
extract style ngspice()
extract do local
extract do capacitance
extract do coupling
extract no resistance
extresist threshold 0
extresist minres 0
extresist mindelay 0
extresist simplify off
extract all
extresist all
feedback clear
antennacheck
set count [feedback count]
feedback save antenna.feedback
set report [open antenna.count w]
puts $report $count
close $report
ext2spice lvs
ext2spice cthresh 0
ext2spice rthresh 0
ext2spice extresist on
ext2spice scale off
ext2spice -o extracted.spice
set report [open completed.txt w]
puts $report completed
close $report
""".replace("load TOP", "load " + tcl(top))
    script = 'if {[catch {\n' + script + '\n} message]} {puts stderr "FLOW_ERROR: $message"}\nquit -noprompt\n'
    (directory / "run.tcl").write_text(script, encoding="utf-8")
    (directory / "empty.rc").write_text("", encoding="ascii")
    args = [linux_path(binary), "-dnull", "-noconsole", "-rcfile", "empty.rc", "-T", "sky130A.tech", "run.tcl"]
    if os.name == "nt":
        args = ["wsl.exe", "-d", os.environ.get("MAGIC_WSL_DISTRO", "Ubuntu"), "--cd", linux_path(directory), "--exec", *args]
    result = {"directory": str(directory), "pdk_revision": revision(),
              "input_sha256": hashlib.sha256((directory / "input.gds").read_bytes()).hexdigest(),
              "technology_sha256": hashlib.sha256(tech.read_bytes()).hexdigest()}
    try:
        proc = subprocess.run(args, cwd=directory, capture_output=True, timeout=timeout,
                              creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        log = (proc.stdout + proc.stderr).decode("utf-8", errors="replace")
        (directory / "magic.log").write_text(log, encoding="utf-8")
        result["log"] = log[-24000:]
        result["engine_version"] = re.search(r"Magic .*", log).group(0) if re.search(r"Magic .*", log) else "Magic"
        if proc.returncode or not (directory / "completed.txt").is_file() or "FLOW_ERROR:" in log:
            raise ValueError("Magic did not complete; inspect magic.log")
        if re.search(r"^(?:Error:|Cannot )", log, re.M):
            raise ValueError("Magic reported an extraction error; inspect magic.log")
        version = re.search(r"Magic (\d+)\.(\d+) revision (\d+)", log)
        if not version or tuple(map(int, version.groups())) < (8, 3, 679):
            raise ValueError("Magic 8.3.679 or newer is required for corrected capacitance extraction")
        if not (directory / "extracted.res.ext").is_file():
            raise ValueError("Magic produced no resistance extraction artifact")
        netlist = (directory / "extracted.spice").read_text()
        devices = len(re.findall(r"^[XM]", netlist, re.M | re.I))
        if not devices:
            raise ValueError("No transistor devices extracted; cannot validate antenna coverage")
        count = int((directory / "antenna.count").read_text().strip())
        result["antenna"] = {"status": "fail" if count else "pass", "feedback_count": count,
                             "feedback": (directory / "antenna.feedback").read_text(), "checked_devices": devices}
        result["pex"] = {"status": "pass", "mode": "RC", "netlist": netlist,
                         "resistors": len(re.findall(r"^R", netlist, re.M)),
                         "capacitors": len(re.findall(r"^C", netlist, re.M)), "devices": devices}
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        result.update({k: {"status": "error", "reason": str(exc)} for k in ("pex", "antenna")})
    (directory / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result
