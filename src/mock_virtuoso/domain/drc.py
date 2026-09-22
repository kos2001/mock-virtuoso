"""A small, honest design-rule check over what a cellview actually holds.

Until now this session would draw anything. A 0.001 µm wire, two straps
overlapping by a hair, a rectangle at x=0.0037 on a 5 nm grid — all of it
built cleanly and read back cleanly, because nothing looked. A layout tool
that cannot say "that is too narrow" teaches an agent that its layout is fine.

WHAT THIS IS NOT. Not sign-off, not Assura, not PVS, and not a real PDK. The
numbers below are this mock's own, named `mockTech` like the tech file they
belong to, and they are internally consistent rather than taken from any
foundry. A clean result here is evidence that the shapes obey *these* rules
and nothing more — which is exactly the distinction the report has to keep,
so `severity` and the catalogue in `skills/design-floor/DRC.md` exist to say
what each code does and does not mean.

Codes are this application's own, in the manner of the Sign-off Hub's
DRC-XXX ladder: they imitate the shape of industry names without being them,
so the catalogue is the only place their meaning lives. Do not infer a rule
from its code.
"""

from __future__ import annotations

from dataclasses import dataclass

# The manufacturing grid, in microns. Every coordinate must land on it.
GRID = 0.005

# Slack on every minimum, in microns. A shape drawn at exactly the minimum is
# legal, and `x1 - x0` for such a shape is only as exact as binary floating
# point allows: of the 2001 grid positions a 0.14 µm met1 wire can start at,
# 919 subtract to 0.13999999999999999. Without this the checker calls half of
# all minimum-width geometry a violation, which is the fastest way to get a
# checker switched off. Representation error here is ~1e-16 µm and the grid is
# 5e-3 µm, so this sits far above the noise and far below any real violation.
EPS = 1e-9

# Per-layer minimums in microns: width, spacing to another shape on the same
# layer, and area. `text` is annotation and has no physical extent, so it is
# absent here rather than given a zero that would read as a checked pass.
RULES: dict[str, dict[str, float]] = {
    "nwell": {"width": 0.840, "space": 1.270, "area": 0.700},
    "diff":  {"width": 0.150, "space": 0.270, "area": 0.045},
    "poly":  {"width": 0.150, "space": 0.210, "area": 0.030},
    "met1":  {"width": 0.140, "space": 0.140, "area": 0.083},
    "met2":  {"width": 0.140, "space": 0.140, "area": 0.067},
    "met3":  {"width": 0.300, "space": 0.300, "area": 0.240},
}

SEVERITY = {
    "DRC-WIDTH-001": "error",
    "DRC-SPACE-001": "error",
    "DRC-GRID-001": "error",
    "DRC-AREA-001": "warn",
}


@dataclass(frozen=True)
class Violation:
    code: str
    severity: str
    layer: str
    measured: float
    required: float
    where: str

    def __str__(self) -> str:
        # Each code measures a different quantity, and printing them all as
        # "a < b µm" made an off-grid coordinate read as a too-small width
        # and an area read as a length. The unit is part of the measurement.
        if self.code == "DRC-GRID-001":
            body = (f"{self.measured:g} is not a multiple of the "
                    f"{self.required:g} µm grid")
        elif self.code == "DRC-AREA-001":
            body = f"{self.measured:g} µm² < {self.required:g} µm² minimum"
        elif self.code == "DRC-SPACE-001":
            body = f"{self.measured:g} µm gap < {self.required:g} µm minimum"
        else:
            body = f"{self.measured:g} µm wide < {self.required:g} µm minimum"
        return f"{self.code} [{self.severity}] {self.layer}: {body} at {self.where}"


def _rect(bbox) -> tuple[float, float, float, float] | None:
    """(x0, y0, x1, y1) from a bBox, normalised, or None if it is not one."""
    try:
        (x0, y0), (x1, y1) = bbox
        x0, y0, x1, y1 = float(x0), float(y0), float(x1), float(y1)
    except (TypeError, ValueError):
        return None
    return min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)


def _gap(a, b) -> float:
    """Edge-to-edge distance between two rectangles; 0 if they touch or overlap."""
    dx = max(b[0] - a[2], a[0] - b[2], 0.0)
    dy = max(b[1] - a[3], a[1] - b[3], 0.0)
    if dx == 0.0 and dy == 0.0:
        return 0.0
    if dx == 0.0:
        return dy
    if dy == 0.0:
        return dx
    return (dx * dx + dy * dy) ** 0.5


def _off_grid(value: float) -> bool:
    """True if a coordinate does not land on the manufacturing grid.

    Compared in grid units with a tolerance, because 0.1/0.005 is 19.999...
    in binary floating point and an exact remainder test calls every third
    honest coordinate a violation.
    """
    units = value / GRID
    return abs(units - round(units)) > 1e-6


def check(cellview) -> list[Violation]:
    """Every violation in this cellview's own shapes, in a stable order.

    Instances are not descended into: a master is checked when the master is
    checked, and reporting a cell's violations again under every placement of
    it buries the one occurrence that needs fixing. What this does not check
    is stated plainly rather than assumed clean — see the catalogue.
    """
    found: list[Violation] = []
    by_layer: dict[str, list[tuple]] = {}

    for shape in cellview.get_prop("shapes"):
        layer = shape.layer
        limits = RULES.get(layer)
        rect = _rect(shape.bbox)
        if rect is None:
            continue
        x0, y0, x1, y1 = rect
        where = f"({x0:g} {y0:g}) ({x1:g} {y1:g})"

        if limits is None:
            # A layer with no entry is a layer nothing is claimed about —
            # `text` is annotation and is never manufactured, so the grid
            # does not apply to it either. Checking it would report a
            # violation that has no fix.
            continue
        by_layer.setdefault(layer, []).append((rect, where))

        for value in rect:
            if _off_grid(value):
                found.append(Violation("DRC-GRID-001", SEVERITY["DRC-GRID-001"],
                                       layer, value, GRID, where))
                break

        narrow = min(x1 - x0, y1 - y0)
        if narrow < limits["width"] - EPS:
            found.append(Violation("DRC-WIDTH-001", SEVERITY["DRC-WIDTH-001"],
                                   layer, narrow, limits["width"], where))
        area = (x1 - x0) * (y1 - y0)
        if area < limits["area"] - EPS:
            found.append(Violation("DRC-AREA-001", SEVERITY["DRC-AREA-001"],
                                   layer, area, limits["area"], where))

    for layer, rects in by_layer.items():
        limit = RULES[layer]["space"]
        for i, (a, where_a) in enumerate(rects):
            for b, where_b in rects[i + 1:]:
                gap = _gap(a, b)
                # Touching or overlapping shapes are one piece of metal, not a
                # spacing error. Calling an abutted row a violation is how a
                # checker gets switched off.
                if EPS < gap < limit - EPS:
                    found.append(Violation(
                        "DRC-SPACE-001", SEVERITY["DRC-SPACE-001"], layer,
                        gap, limit, f"{where_a} to {where_b}"))
    return found


def summary(violations: list[Violation]) -> dict[str, int]:
    """How many of each code, for a report that counts before it quotes."""
    counts: dict[str, int] = {}
    for v in violations:
        counts[v.code] = counts.get(v.code, 0) + 1
    return counts
