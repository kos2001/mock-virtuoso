"""Installed, pinned SKY130 model profiles (no user supplied SPICE paths)."""
from pathlib import Path
import hashlib
import os
import re

REVISION = "0c1df35fd535299ea1ef74d1e9e15dedaeb34c32"
CORNERS = ("tt", "ff", "ss", "fs", "sf")
ROOT = Path(__file__).resolve().parents[2]


def installed():
    configured = os.environ.get("SKY130_MODEL_ROOT")
    candidates = [Path(configured)] if configured else [
        ROOT / ".tools" / folder / "ciel/sky130/versions" / REVISION / "sky130A"
        for folder in ("pdks-linux", "pdks")]
    return next((p.resolve() for p in candidates
                 if (p / "libs.tech/ngspice/sky130.lib.spice").is_file()), None)


def revision():
    return "operator-provided" if os.environ.get("SKY130_MODEL_ROOT") else REVISION


def models(corner):
    """Flatten only the selected library section; hash every consumed source."""
    if corner not in CORNERS:
        raise ValueError("Unsupported SKY130 corner")
    root = installed()
    if root is None:
        raise ValueError("SKY130 models are not installed")
    sources = {}

    def expand(path, stack=()):
        path = path.resolve()
        if not path.is_relative_to(root) or path in stack:
            raise ValueError("Invalid PDK include dependency")
        content = path.read_bytes()
        sources[str(path.relative_to(root)).replace("\\", "/")] = hashlib.sha256(content).hexdigest()
        lines, active = [], True
        for line in content.decode("utf-8").splitlines():
            section = re.match(r"^\s*\.lib\s+(\w+)\s*$", line, re.I)
            if section:
                active = section[1].lower() == corner
                continue
            if re.match(r"^\s*\.endl\b", line, re.I):
                active = True
                continue
            if not active:
                continue
            include = re.match(r'^\s*\.inc(?:lude)?\s+["\x27]?([^"\x27\s]+)', line, re.I)
            lines.append(expand(path.parent / include[1], (*stack, path)) if include else line)
        return "\n".join(lines)

    text = expand(root / "libs.tech/ngspice/sky130.lib.spice") + "\n"
    return text, {"profile": "sky130", "corner": corner, "revision": revision(),
                  "source_files": sources, "sha256": hashlib.sha256(text.encode()).hexdigest(),
                  "qualification": "Public PDK; foundry sign-off approval not established"}
