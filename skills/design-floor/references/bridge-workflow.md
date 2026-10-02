# Bridge execution and evidence

## Select the backend before the API

The installed bridge was analyzed at upstream `Arcadia-1/virtuoso-bridge-lite`
commit `cf6344cff410bcbd32fd6fe595a53d1fdbeeb7c3` (package 0.8.0).
The project imports it from `.tools/virtuoso-bridge-lite` in this environment;
other installations may differ. The authoritative local entrypoint is that
checkout's `skills/virtuoso/SKILL.md`, with `references/layout-python-api.md`,
`layout-skill-api.md`, `local-docs.md` and `troubleshooting.md` alongside it.
Recheck those references after an update; do not infer compatibility from the
package version alone.

| Task | Mock design floor | Real Cadence endpoint |
|---|---|---|
| Connect | Existing `floor/lanes.env` and assigned profile; the floor owns daemon lifecycle | Existing profile, bridge status, explicit target CIW |
| Discover | `mockCapabilities()`; a returned name promises only the mock subset | `doc-info`, `skill-find NAME`, `skill-info NAME`; `doc-search` for missing concepts |
| Layout | Supported `client.layout` calls or documented inline SKILL; read back geometry | Prefer documented Python layout API; verify PDK cells and signatures |
| Schematic/ERC | `mockCircuitLoad/Read/ERC/Netlist/Simulate`; limited `schCheck` | `client.schematic` and installed documentation |
| Maestro | Not implemented; project PVT/PEX workflows are separate services | Documented `client.maestro` and actual simulator availability |
| DRC/LVS | `mockDrcCheck` is educational; external verification is a separate workflow | Configured rule decks and licensed engines; a bridge connection does not provide them |

Never run `mock*` extensions on real Cadence. If backend identity is unknown,
resolve the configured target first. Failure of `mockCapabilities()` on an old
mock does not prove it is real Cadence. Stop capability-dependent work until
the server version is established. Do not start/stop a daemon, dismiss a dialog,
or change profiles simply because a call failed. The upstream dialog inspection
guard is opt-in; inspection does not authorize dismissal of another user's CIW.

## Execution and decoding

For local floor lanes, use `tools/floor_skill.py --env floor/lanes.env -p LANE
--stdin` with the repository Python (or `--file path.il`). The audited upstream
CLI's `from_env()` path can reach a local daemon without acquiring its token;
the project runner uses authenticated `VirtuosoClient.local()` instead and
rejects nonlocal/mismatched lane configurations. Never disable authentication.
For real Cadence, use the documented upstream CLI `eval --stdin`.
Python is useful when combining
structured API calls and machine-readable reports. `VirtuosoResult.status`
must be success before interpreting `output`; retain errors and warnings.
The final expression is the return value. `printf` output and a successful
transport are not evidence that a design check passed.

Mock discovery returns a SKILL string containing JSON. Raw protocol output may
retain the outer SKILL string quotes; decode that string before parsing its JSON.
For these JSON-returning extensions, this works with quoted or unquoted output:

```python
import json

def read_json_result(result):
    if getattr(result.status, "value", result.status) != "success":
        raise RuntimeError(result.errors)
    value = json.loads(result.output)
    return json.loads(value) if isinstance(value, str) else value

caps = read_json_result(client.execute_skill("mockCapabilities()"))
assert caps["backend"] == "mock-virtuoso"
report = read_json_result(client.execute_skill(
    'mockInspectCell("STDLIB" "INV" "layout")'))
```

Pass identifiers and JSON as SKILL string literals, not interpolated source.
Within this repository, `mock_virtuoso.skill.values.skill_repr(value)` escapes
strings. Do not serialize Python `repr()` into SKILL. Do not log bridge tokens.

## Mutations, retry and ownership

Before writing, record library/cell/view, assigned owner, mode (new/replacement
or incremental edit), dependencies and expected postconditions. Query
`mockInspectCell` before opening an unknown cell. It does not create the cell,
change its mode, switch windows or run validation.

For replacement only, `mock_virtuoso.bridge_compat.clear_layout` checks a bounded
clear of shapes, instances and nets; require its returned `True` before building.
`build_layout` chooses `layout.create` or the older explicit `edit(mode="w")`.
Some bridge builders bind the active window, so always verify the resulting
library/cell/view; do not assume a requested name proves the edited target.
For incremental edits, use the documented modify API; never clear as recovery.

After errors/timeouts, read back first. Effects before a failure remain. Compare
counts and geometry to the pre-edit state and intended result before retrying.
Concurrent work is safe only with disjoint cell ownership; read another lane's
output without reopening it into a different mode. A missing master is a blocked
dependency, not permission to fabricate a replacement.

The executable example `../examples/owned-layout.il` deliberately uses a scratch
cell in write mode. Run it only on an isolated server or an explicitly disposable
owned cell. The contract tests execute it twice and verify pins/nets/shapes do
not accumulate. It is a connectivity example, not a standard cell or LVS proof.

## Verification and handoff

Use this evidence sequence for a design change:

1. Geometry read-back: exact target, counts by object type/layer, bbox, real
   nets/terminals/pins, masters and transforms where relevant. Labels are data.
   Imported GDS pin-purpose polygons do not automatically create mock DB nets
   or terminals. Zero DB pins does not establish that the source GDS lacks pins;
   inspect/extract the original GDS with the applicable PDK for LVS.
2. Mock DRC: record `mockDrcCheck` violations with the scope of `../DRC.md`.
   An empty list means those educational rules passed only.
3. Circuit ERC/netlist/simulation: use loaded circuit JSON, model profile,
   analysis/corner and actual engine report. ERC success is not LVS success.
4. External DRC/LVS/PEX: use the project's Verification panel/service, record
   the uploaded GDS, reference SPICE, top cell, port mapping, PDK/rule deck,
   engine version, input hashes, status, reports/logs. A selected Drawing cell
   is not automatically the uploaded GDS. Compare artifacts from the same input
   revision; changes make prior results stale.
5. Foundry-qualified sign-off: requires the applicable qualified tools/decks
   and acceptance criteria. Neither mock DRC nor open-source tool availability
   alone establishes it. Report unavailable checks as `not_run`, execution
   failures as `error`, and actual rule/match failures as `fail`.

Handoff fields: target and owner; change and expected postconditions; before/after
read-back; check status with input identity and artifact paths; unsupported or
blocked work; remaining dependency. State exactly what was executed. Native
Xschem editing, full PCells and arbitrary Maestro flows must not be claimed from
bridge API names alone.
