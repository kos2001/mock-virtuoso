"""End-to-end demonstration: drive virtuoso-bridge-lite's Python API against mock-virtuoso.

Nothing here talks to the mock directly. Every action goes through the same
`VirtuosoClient` calls you would use against a real Cadence Virtuoso, over the
same TCP protocol. The only difference is which process is listening.

Run:  .venv/bin/python demo/demo_layout_session.py
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from mock_virtuoso.server import MockVirtuosoServer
from mock_virtuoso.session import Session

from virtuoso_bridge import ExecutionStatus, VirtuosoClient
from virtuoso_bridge.virtuoso.layout import (
    layout_create_label,
    layout_create_param_inst,
    layout_create_path,
    layout_create_rect,
    layout_create_via_by_name,
    layout_read_geometry,
    layout_select_box,
    layout_set_active_lpp,
    layout_show_only_layers,
    parse_layout_geometry_output,
)

LIB, CELL = "DEMO", "INV"
step = 0


def head(title: str) -> None:
    global step
    step += 1
    print(f"\n{'─' * 72}\n{step}. {title}\n{'─' * 72}")


def show(label: str, result) -> None:
    status = getattr(result, "status", None)
    if status is ExecutionStatus.SUCCESS:
        out = (result.output or "").strip()
        print(f"   ✓ {label}" + (f" → {out[:60]}" if out and len(out) < 62 else ""))
    else:
        print(f"   ✗ {label} → {result.errors}")


def main() -> int:
    artifacts = Path(tempfile.mkdtemp(prefix="virtuoso-demo-"))
    with MockVirtuosoServer(Session(artifact_dir=artifacts)) as server:
        client = VirtuosoClient.local(port=server.port)

        head("Connect — exactly as against a real Virtuoso daemon")
        print(f"   VirtuosoClient.local(port={server.port})")
        print(f"   test_connection()      → {client.test_connection()}")
        show("execute_skill('1+2')", client.execute_skill("1+2"))

        head("Open a layout window")
        show("open_window(DEMO/INV, view='layout')",
             client.open_window(LIB, CELL, view="layout"))
        print(f"   get_current_design()   → {client.get_current_design()}")
        print(f"   list_windows()         → {client.list_windows()}")

        head("Build the layout — batched through client.layout.edit()")
        with client.layout.edit(LIB, CELL) as ed:
            ed.add(layout_set_active_lpp("met1"))
            # device-ish rectangles
            ed.add(layout_create_rect("nwell", "drawing", -1.0, -1.0, 5.0, 7.0))
            ed.add(layout_create_rect("poly", "drawing", 1.5, 0.0, 2.5, 6.0))
            ed.add(layout_create_rect("diff", "drawing", 0.0, 3.5, 4.0, 6.0))
            ed.add(layout_create_rect("diff", "drawing", 0.0, 0.0, 4.0, 2.5))
            # routing
            ed.add(layout_create_path("met1", "drawing", [(2.0, 6.0), (2.0, 8.0)], 0.4))
            ed.add(layout_create_path("met1", "drawing", [(4.0, 3.0), (6.0, 3.0)], 0.4))
            ed.add(layout_create_via_by_name("M1_M2", 6.0, 3.0))
            # pins
            ed.add(layout_create_label("text", "drawing", 2.0, 8.0, "IN",
                                       "centerCenter", "R0", "stick", 0.3))
            ed.add(layout_create_label("text", "drawing", 6.0, 3.0, "OUT",
                                       "centerCenter", "R0", "stick", 0.3))
        print(f"   {len(ed.commands)} SKILL ops sent as ONE round trip, then saved")

        head("Hierarchy — place the cell inside a top level")
        with client.layout.edit(LIB, "TOP") as ed2:
            ed2.add(layout_create_param_inst(LIB, CELL, "layout", "I0", 0, 0, "R0"))
            ed2.add(layout_create_param_inst(LIB, CELL, "layout", "I1", 20, 0, "MY"))
        print("   two instances of DEMO/INV placed in DEMO/TOP")

        head("Read it back — with the BRIDGE's own reader, not ours")
        res = client.execute_skill(layout_read_geometry(LIB, CELL))
        rows = parse_layout_geometry_output(res.output)
        print(f"   parse_layout_geometry_output() → {len(rows)} rows")
        for r in rows:
            if r.get("kind") == "shape":
                print(f"     {r['objType']:8} {r['layer']:6} bbox={r['bbox']}")
        top = parse_layout_geometry_output(
            client.execute_skill(layout_read_geometry(LIB, "TOP")).output)
        for r in top:
            if r.get("kind") == "instance":
                print(f"     inst {r['name']:3} {r['lib']}/{r['cell']} @ {r['xy']} {r['orient']}"
                      f" bbox={r['bbox']}")

        head("Select + batch-fetch — the bridge's N-attributes-in-one-call API")
        client.execute_skill(layout_show_only_layers([("met1", "drawing")]))
        sel = client.execute_skill(layout_select_box((-2.0, -2.0, 8.0, 9.0)))
        print(f"   layout_select_box()    → {sel.output}")
        objs = client.fetch("geGetSelSet()", ["objType", "lpp"])
        print(f"   fetch(geGetSelSet(), ['objType','lpp']) -> {len(objs)} objects, ONE round trip")
        for o in objs[:4]:
            print(f"     {o}")

        head("Screenshot — a real file the bridge downloads")
        shot = artifacts / "inv_layout.png"
        r = client.screenshot(output=shot, target="layout")
        if shot.exists():
            print(f"   ✓ {shot.name}  {shot.stat().st_size} bytes, PNG magic="
                  f"{shot.read_bytes()[:4]!r}")
        else:
            print(f"   screenshot → {r.status} {r.errors}")

        head("Out-of-scope surface fails LOUDLY instead of lying")
        for skill in ("maeOpenSetup()", "schCreateWire(cv nil nil)"):
            res = client.execute_skill(skill)
            print(f"   {skill:28} → {res.status.name}: {res.errors[0] if res.errors else res.output}")

        print(f"\n{'═' * 72}")
        print("Every call above is the real virtuoso-bridge-lite API.")
        print("No Cadence licence, no EDA server, no Virtuoso process.")
        print(f"Artifacts: {artifacts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
