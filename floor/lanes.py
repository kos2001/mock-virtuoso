"""Which lanes the floor has, read from the briefs that describe them.

Kept apart from `design_floor` so it can be imported without virtuoso-bridge:
the briefs are the floor's contract with its agents, and checking that contract
should not require the bridge to be installed.
"""

from __future__ import annotations

import re
from pathlib import Path

ROLES = Path(__file__).resolve().parent.parent / "skills" / "design-floor" / "roles"


def read_lanes(directory: Path = ROLES) -> dict[str, str]:
    """One lane per brief, named and described by the brief itself.

    A lane with no brief leaves an agent nothing to read, and a brief with no
    lane is a file nobody opens. Deriving one from the other means neither can
    happen: adding a lane *is* writing its brief.

    Each brief opens with:  # Lane `name` — what this lane does
    """
    lanes: dict[str, str] = {}
    for path in sorted(directory.glob("*.md")):
        heading = path.read_text(encoding="utf-8").splitlines()[0]
        match = re.match(r"#\s*Lane\s*`([a-z][a-z0-9_]*)`\s*[—-]\s*(.+)", heading)
        if not match:
            raise ValueError(
                f"{path.name}: first line should be '# Lane `name` — role', got {heading!r}")
        name, role = match.group(1), match.group(2).strip()
        if name != path.stem:
            raise ValueError(f"{path.name}: declares lane {name!r}; name the file after the lane")
        lanes[name] = role
    if not lanes:
        raise ValueError(f"no lane briefs in {directory}")
    return lanes
