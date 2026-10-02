"""Read-only mock discovery. These extensions are not Cadence SKILL APIs."""
import json
from collections import Counter

from mock_virtuoso.skill.errors import SkillError


def install(session):
    def capabilities(it, args, kwargs):
        if args or kwargs:
            raise SkillError("mockCapabilities expects no arguments")
        return json.dumps({
            "schema_version": 1,
            "backend": "mock-virtuoso",
            "functions": it.callable_names(),
            "accepted_noops": ["hiRedraw", "hiFlush", "hiZoomAbsoluteScale"],
            "extensions": {
                "mockCapabilities": "mockCapabilities() -> JSON string",
                "mockInspectCell": 'mockInspectCell(lib cell view) -> JSON string; never opens or creates',
                "mockDrcCheck": "mockDrcCheck(cv) -> violation strings; educational rules only",
                "mockCircuitLoad": "mockCircuitLoad(schematicCV circuitJSON) -> t; replaces circuit",
                "mockCircuitRead": "mockCircuitRead(schematicCV) -> circuit JSON string",
                "mockCircuitERC": "mockCircuitERC(schematicCV) -> ERC JSON string",
                "mockCircuitNetlist": "mockCircuitNetlist(schematicCV) -> SPICE string",
                "mockCircuitSimulate": "mockCircuitSimulate(schematicCV) -> report JSON string; writes artifacts",
            },
            "limitations": [
                "Registered names describe a subset, not full Cadence semantics.",
                "schCheck is a limited circuit ERC adapter; other sch*/mae* APIs are unsupported.",
                "No foundry sign-off via SKILL; external DRC/LVS reports require their own provenance.",
                "Database is in memory; dbSave is not durable disk persistence.",
                "Failed mutations are not rolled back; do not blindly retry.",
                "Read-mode dbOpenCellViewByType can create an absent cell and changes shared open mode.",
            ],
        })

    def inspect_cell(it, args, kwargs):
        if kwargs or len(args) != 3 or not all(isinstance(a, str) and a for a in args):
            raise SkillError("mockInspectCell expects three nonempty strings: lib cell view")
        cv = session.design.find_cellview(*args)
        report = {"schema_version": 1, "backend": "mock-virtuoso",
                  "target": dict(zip(("library", "cell", "view"), args)),
                  "exists": cv is not None}
        if cv is not None:
            shapes = cv.get_prop("shapes")
            nets = cv.get_prop("nets")
            report.update({
                "view_type": cv.view_type,
                "counts": {"shapes": len(shapes), "instances": len(cv.get_prop("instances")),
                           "nets": len(nets), "terminals": len(cv.get_prop("terminals")),
                           "pins": sum(len(n.get_prop("pins")) for n in nets)},
                "layers": dict(sorted(Counter(f"{s.layer}/{s.purpose}" for s in shapes).items())),
                "bbox": cv.bbox,
                "circuit_loaded": bool(cv.circuit),
                "verification": "not_run",
            })
        return json.dumps(report)

    session.interp.register("mockCapabilities", capabilities)
    session.interp.register("mockInspectCell", inspect_cell)
