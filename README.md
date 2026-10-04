<img src="assets/icon.svg" width="72" height="72" align="left" alt="" style="margin-right:14px"/>

# mock-virtuoso

<br clear="left"/>


A test double that speaks the Cadence RAMIC bridge TCP protocol and
interprets a subset of Cadence SKILL, so `virtuoso-bridge-lite` can be
developed and tested without a real Cadence Virtuoso installation.

`mock-virtuoso` listens on a TCP port, accepts the same wire protocol the
real RAMIC bridge daemon (`ramic_bridge_daemon_3.py`) speaks, evaluates the
SKILL it receives against an in-memory design database (cellviews, shapes,
instances, windows, layer/purpose palette), and replies with the same
byte-level success/failure framing the real daemon uses.

## What this is not

The SKILL core is a test double, not a replacement for Virtuoso or a foundry
sign-off tool. Its `mockDrcCheck` uses mockTech rules. The optional verification
workflow below runs real open-source KLayout DRC, LVS and density decks on
external SKY130 GDS/SPICE inputs. The core implements a subset of SKILL's syntax and a
subset of the `db*`/`dd*`/`tech*`/`hi*`/`ge*`/`le*`/`pte*` function families
to let a bridge client create, read back, select, and delete layout
geometry and to exercise the protocol layer. A declarative circuit editor now
provides structural ERC, SPICE export and real ngspice simulation. Its explicit
`mockCircuit*` extensions and limited `schCheck` work on imported circuit graphs;
general Cadence schematic drawing (`schCreate*`) and Maestro (`mae*`) APIs remain
unimplemented and fail with `unknown function`.

## Install

### Agents using the SKILL bridge

Start with [AGENTS.md](AGENTS.md) and the
[design-floor skill](skills/design-floor/SKILL.md). The
[bridge workflow](skills/design-floor/references/bridge-workflow.md) maps
mock versus real Cadence APIs, safe retries, JSON result decoding and DRC/LVS
evidence. On a known mock endpoint, `mockCapabilities()` returns the installed
callable names and limitations; `mockInspectCell("LIB" "CELL" "layout")`
returns counts, layers, bbox and presence without opening or creating a cell.
Both return JSON strings and are mock-only extensions. Restart an older daemon
with its existing data restoration procedure before using newly added functions.

### Python environment

```bash
uv venv .venv && source .venv/bin/activate
uv pip install -e ".[dev]"
```

### Open-source physical verification

The Design Floor includes a **PDK · DRC / LVS** panel with guided PDK, rules and GDS/SPICE
inputs for **real KLayout SKY130 DRC and LVS**. This is separate from `mockDrcCheck`:
mockTech geometry is not a SKY130 PDK layout and is not automatically remapped.

Project constraints support minimum width/spacing (`value_um`) and minimum
connected-polygon area (`kind: "min_area"`, `value_um2`). Area checks operate on
merged hierarchical geometry and report measured area and violation locations.

### Circuit editing, ERC and analog simulation

Use **회로 · 시뮬레이션** in the existing Design Floor. Edit components and named nets,
inspect the connection diagram, check ERC, export SPICE, and run ngspice without
leaving the page. Components: R, C, L, independent voltage/current sources, diodes
and four-terminal NMOS/PMOS (D,G,S,B order). Values use SI units; node `0` is ground.
Diodes and level-1 MOS use **generic demonstration models**, not foundry PDK models.

The editor offers operating point, DC source sweep, AC frequency response
(complex magnitude/phase retained) and transient analysis, plus temperature.
Pulse sources can be imported in circuit JSON with `low`, `high`, `delay`, `rise`,
`fall`, `width`, `period` under a source's `pulse` field. Results include vectors,
logs, engine version, input hash and exportable JSON. At most 2001 samples are
displayed; complete raw data stays in `simulation-runs/<id>/`.

Structural ERC rejects missing ground, dangling nets, structural DC-floating nets,
shorted two-terminal components and ideal voltage-source/inductor loops. AC runs
require AC excitation. ERC failures block simulation; missing engines, timeouts and
invalid output never count as successful runs. This is a connectivity screen,
not foundry electrical reliability checking.

Install the official pinned Windows engine into this checkout:

```powershell
.venv/Scripts/python.exe -m pip install py7zr
.venv/Scripts/python.exe tools/fetch_ngspice.py
```

Alternatively set `NGSPICE_EXE` or install `ngspice` on PATH. The downloader uses
the [official ngspice distribution](https://ngspice.sourceforge.io/download.html)
and verifies the archive SHA-256. Execution uses the documented
[`-n -b -r` batch interface](https://ngspice.sourceforge.io/docs/ngspice-manual.pdf).

The UI saves settings in the browser and supports JSON import/export.
The header and both tool dialogs offer Korean/English and light/dark/system
preferences. Switching language preserves circuit values, uploaded files and
results; engine logs, netlists, signal names and report data retain their source
representation.

The circuit window includes runnable CMOS examples for INV, BUF, NAND2, NOR2,
AND2, OR2, XOR2, XNOR2, MUX2, AOI21 and OAI21. Select a standard cell and load it
to populate the SKY130 testbench with 1.8 V input pulses and a 5 fF output load.
These are educational transistor circuits, not qualified foundry standard-cell
layout or timing views. Inputs cycle through every Boolean combination; A is
the fastest input and the last input is the slowest. The default experiment
measurement checks peak output voltage, not the complete truth table.

For actual layouts in the central Drawing canvas, run:

```powershell
.venv/Scripts/python.exe tools/load_standard_cells.py --fetch
```

This downloads pinned public SKY130 HD GDS/SPICE files and their license, then
loads 12 cells into the running floor's `SKY130_EXAMPLES` library: INV, BUF,
NAND2, NOR2, AND2, OR2, XOR2, XNOR2, MUX2, AOI21, OAI21 and DFF (all `_X1`).
Use the **Layout cell / 레이아웃 셀** selector above the canvas. Coordinates
remain in µm; source layer/datatype distinctions and polygon holes are retained.
The cache includes file hashes and upstream URLs. The loader preserves existing
cells, including `DEMO/CELL`, and installed examples reload when the floor next
starts. These imported layouts and the educational simulation examples are
separate views; the import does not assert LVS equivalence or sign-off.

After **Run simulation**, the dialog scrolls to the waveform viewer. Standard
cell examples enable stacked input/output traces automatically. Toggle traces,
zoom and pan the shared axis, or move the pointer/keyboard-accessible cursor
to inspect the nearest displayed sample. Time/frequency values use engineering
units; the viewer indicates the raw and displayed sample counts. Last-value
tables and engine logs remain available in expandable sections.

**설계 DB에 저장** replaces the named `CIRCUITS/<name>/schematic` graph in the
existing server through its SKILL bridge; **DB에서 불러오기** loads that name.
The mock database is in memory: export JSON for persistence across server restarts.
Agents can use `mockCircuitLoad(cv json)`, `mockCircuitRead(cv)`, `mockCircuitERC(cv)`,
`mockCircuitNetlist(cv)` and `mockCircuitSimulate(cv)` on a schematic cellview.
`schCheck(cv)` returns error/warning counts for a graph loaded by `mockCircuitLoad`;
it does not infer connectivity from arbitrary schematic drawings.

```powershell
.venv/Scripts/python.exe -m mock_virtuoso.cli circuit circuit.json --action check
.venv/Scripts/python.exe -m mock_virtuoso.cli circuit circuit.json --action netlist
.venv/Scripts/python.exe -m mock_virtuoso.cli circuit circuit.json --action simulate
```

The existing circuit window also supports **SKY130 1.8 V NMOS/PMOS models**,
TT/FF/SS/FS/SF corners, and an experiment manager with temperature/source/RLC
sweeps, measurements, acceptance bounds, result comparison and persistent history.
Measurements use every raw sample; `mean` is the arithmetic sample mean.
Experiments are limited to 30 combinations and 16 measurements. Use
`POST /api/circuit/experiment` for multiple measurement definitions;
`GET /api/circuit/history` lists the latest 30 experiments.
This is an independent workflow, not Cadence Maestro API compatibility.

On Windows with WSL Ubuntu, install the reproducible PDK/extraction profile:

```powershell
.venv/Scripts/python.exe tools/bootstrap_pdk.py --system-deps
```

This installs build dependencies inside Ubuntu, ciel 3.0.0, SKY130 primitives
at `0c1df35fd535299ea1ef74d1e9e15dedaeb34c32`, and Magic 8.3.684 at
`4f53bb3091d1e4a9b2009a58f157a8a4331d4c84` under `.tools`.
Subsequent installations can omit `--system-deps`. For another distribution,
use `--distro NAME` and set `MAGIC_WSL_DISTRO=NAME` when starting the server.
Simulation jobs snapshot the selected PDK model dependencies as `models.spice`,
including source hashes, corner and revision in their result report.
SI MOS widths/lengths in the editor are converted to the model's micrometre units.
The SKY130 diode, bipolar, RF and other device families are not editor components.
RLC elements remain ideal. Public PDK models do not establish foundry approval.

In the physical verification window, select **Magic PEX·antenna 검사 포함**.
This adds real RC extraction and antenna checks to the review gate, including
for cell scope. Download the extracted SPICE or **검토 자료 ZIP** with the
snapshotted GDS, decks, logs, native results and an external review checklist.
For post-layout simulation, copy the verification run ID from its JSON report
into the circuit window's **Post-layout** section, define sources/RLC loads,
and map every extracted pin to a testbench net. Both PEX and LVS must pass.
Results retain the original verification ID and layout/extracted-netlist hashes.

Full Virtuoso API parity, full Maestro functionality, process ERC, reliability
qualification and foundry-qualified sign-off remain outside this implementation.
The review bundle supports external approval; it does not issue that approval.

### Installing physical verification decks

Install the optional report-reader dependency, the full KLayout application,
and the pinned upstream rule decks:

```powershell
.venv/Scripts/python.exe -m pip install -e ".[verification]"
.venv/Scripts/python.exe tools/fetch_verification_decks.py
$env:KLAYOUT_EXE = "C:/path/to/klayout_app.exe"
.venv/Scripts/python.exe floor/design_floor.py
```

The Python `klayout` package reads geometry and result databases; the full
[KLayout application](https://www.klayout.de/build.html) executes the Ruby decks.
The floor also discovers an unpacked Windows executable under `.tools/klayout`.
Set `SKY130_DECKS` to override the floor's default `.tools/sky130` deck directory.
Open the panel from the existing Design Floor at `http://127.0.0.1:8900`.
It uses the same page and server; closing it preserves the design view and verification inputs.

#### macOS verification setup

Use the repository environment for dependencies and pinned SKY130 decks:

```bash
uv pip install --python .venv/bin/python -e ".[dev,verification]"
.venv/bin/python tools/fetch_verification_decks.py --fixtures
```

Download the full application matching your macOS version and architecture from
the [official KLayout downloads](https://www.klayout.de/build.html). The Python
package alone does not execute the Ruby DRC/LVS decks. Place `klayout.app` in
`.tools/klayout/`, `/Applications/`, or `~/Applications/`; the floor discovers
these locations automatically. `KLAYOUT_EXE` overrides discovery.

For a checkout-local application, run the external integration checks with:

```bash
export KLAYOUT_EXE="$PWD/.tools/klayout/klayout.app/Contents/MacOS/klayout"
.venv/bin/python -m pytest tests/test_verification_integration.py -q
.venv/bin/python floor/design_floor.py
```

For circuit simulation, the [ngspice project](https://ngspice.sourceforge.io/download.html)
recommends Homebrew on macOS (`brew install ngspice`). An existing `ngspice`
on PATH is used automatically; `NGSPICE_EXE` can select another executable.
`fetch_ngspice.py` downloads a Windows executable, and `bootstrap_pdk.py` uses
Windows WSL; neither is a native macOS installer. The deck integration tests
do not install SKY130 transistor models or Magic PEX/antenna support.

### Functional / PVT review and pre/post-layout comparison

In **Circuit · Simulation**, load a standard-cell example and open
**Function · PVT · timing / power · PEX comparison**. Select the expected logic,
input voltage-source IDs in A/B/C order (A/B/S for MUX2), supply source and output
node. Set corners, temperatures, supply voltages and project acceptance limits.
The review regenerates ground-referenced input pulses, scales their high level
with VDD, and keeps the editor's device sizing and RLC loads. Generic models
support temperature/voltage studies but only the `tt` placeholder corner;
process corners require installed SKY130 models.

- All input combinations are sampled at vector midpoints, with low/high limits
  at 20%/80% of supply. Incorrect input stimulus also fails the truth table.
- Delay uses interpolated 50% crossings on observed single-input transitions.
  Output rise/fall uses 10–90% crossings. Multi-input transitions are excluded
  from timing; this does not cover all timing arcs or generate Liberty.
- Supply power uses `-VDD * I(VDD)` integrated over one complete input cycle
  using the full adaptive raw samples, not the downsampled plot or an arithmetic
  sample average. It is stimulus-dependent supply power, not total system power.
- The table retains each PVT combination, measured values, bounds, verdict,
  waveform and truth table. Limits default to educational examples; set the
  actual project specifications. Plans are bounded to 30 simulations.
- **Pre/post PEX comparison** requires a completed verification run with passing
  LVS and PEX plus an exact mapping of all reference/extracted ports. It uses
  that run's snapshotted reference SPICE and RC-extracted circuit with identical
  sources, loads, PVT and criteria. Editor transistors are excluded. Reference
  SHA-256 and extraction/layout identity are checked before simulation. The
  adapter supports flat numeric SKY130 1.8 V nfet/pfet/pfet_hvt X/R/C netlists;
  unsupported models, hierarchy or executable SPICE directives are rejected.
  Paired comparisons allow up to 15 combinations (30 simulations).

The **Design verification dashboard** distinguishes pass, fail, execution error,
not run, unsupported and stale results. Circuit and physical results retain
separate scopes; unrelated green checks are never combined into a sign-off claim.
Input/condition changes mark affected results stale. JSON exports include status,
provenance and raw-run references; results persist under
`simulation-runs/review-*/` and `simulation-runs/comparison-*/`.
Process ERC, block STA, DFF setup/hold, Monte Carlo, IR/EM and foundry-certified
sign-off remain outside this review. These checks require their own tools,
qualified models, constraints and coverage.

### DRC / LVS review workflow

The Drawing toolbar now offers **선택 셀 검증** (selected-cell verification).
It reads the selected `library/cell/layout` and every referenced master through
the read-only `mockLayoutSnapshot` bridge extension, recording geometry,
instance transforms, named nets, terminals and pin-to-shape associations.
A SHA-256 covers the complete hierarchy: changes to a master or connectivity
invalidate the report as well as edits to the top cell. The page checks freshness
every three seconds while a report is loaded, including when the dialog is closed.
Unavailable freshness checks mark the result stale. No cell is opened or created
by this snapshot operation.

The default **mockTech** profile exports educational GDS layer numbers and runs
per-cell mock bounding-box DRC. **SKY130** explicitly selects the project's
SKY130 layer/purpose mapping and runs real KLayout decks on GDS exported from
that snapshot; upload a matching reference SPICE for LVS. Mapping does not
convert mock transistor/via structures into a PDK layout. Unknown mappings,
mock via objects, unresolved instance parameters, empty geometry and coordinates
outside the 0.0001 µm GDS export grid are refused rather than silently omitted
or rounded. Real via polygons imported from GDS are supported.

Each export is read back and compared by per-layer polygon XOR, text and
instance transforms. This checks GDS serialization, not the canvas renderer,
electrical connectivity or functional performance. Those statuses are separate.
Use the existing circuit review and PEX comparison workflow for performance.
Reports retain both the database snapshot hash and exact GDS hash, and can be
downloaded with the checked GDS. `layout-runs/<id>/` stores the immutable DB
snapshot, GDS and report; external verification evidence ZIPs also contain
`layout-snapshot.json` and the source hashes. A stale report remains evidence
about its original inputs and must not be used to approve the current cell.

`POST /api/layout/check` accepts `library`, `cell`, optional `profile`
(`mockTech` or `sky130`), `netlist` and external verification `settings`.
`POST /api/layout/status` accepts the target and `snapshot_sha256` to check
freshness without running DRC/LVS again. An older running daemon must be
restarted with its existing data restoration procedure before using the new
snapshot extension.

The floor's canvas now consumes the same read-only snapshot format, including
path widths and nested master geometry. Paths are drawn along their centreline
with their actual width rather than as filled bounding rectangles. Pixel-level
renderer verification is still separate from GDS readback checks.

The [versioned SKY130 layout bundle](examples/sky130/README.md) contains all
12 Drawing examples as original GDS/reference SPICE, with SVG previews,
upstream source hashes and the original Apache-2.0 license. They can be opened
directly from a clone; startup prefers this bundle over the optional local cache.

The **DRC / LVS** panel puts both checks first, with separate status cards and
an input checklist. It checks the **uploaded GDS and reference SPICE**, not the
cell currently selected in Drawing. For the imported standard-cell examples,
choose the corresponding `.gds` and `.spice` in `.tools/standard-cells`.

1. Select GDS, confirm the exact top cell and installed SKY130 decks.
2. Add self-contained reference SPICE for LVS. Confirm pins, substrate net
   (for example `VNB`) and device dimension units. Without SPICE, DRC can run,
   but LVS is **not run** and the review gate stays blocked.
3. Run verification. DRC checks the enabled FEOL, BEOL, off-grid and floating-metal
   groups. LVS extracts layout devices and compares circuits against SPICE;
   an empty extraction/comparison cannot pass.
4. Review DRC rule names, cell names and marker geometry in the searchable
   location table. Up to 200 matching markers are shown from the report's
   first 1,000 markers; counts and truncation are explicit. Inspect the complete
   `drc.lyrdb` from the evidence ZIP in KLayout when needed.
5. Review LVS circuit pairs and native match statuses. For mismatch details,
   open `lvs.lvsdb` in KLayout and check pins, supply/substrate connections,
   device models and W/L. Engine errors point to `drc.log` or `lvs.log`.
6. Fix the design and upload the revised files, then rerun. Changing inputs or
   settings marks the previous result as stale. Inspect run settings and input/deck
   SHA-256 hashes or download the evidence ZIP to retain exactly what was checked.

**Pass, violations/mismatch, engine error and not run are distinct states.**
DRC/LVS pass does not override failed project constraints or other required
checks. Review readiness remains separate from foundry-certified sign-off.

For batch use:

```powershell
.venv/Scripts/python.exe -m mock_virtuoso.cli verify --klayout $env:KLAYOUT_EXE --gds design.gds --top inverter --netlist design.spice
```

The CLI returns 0 when the selected review gate is ready, 1 for violations,
mismatch, missing required checks or run errors, and 2 for setup/input errors. Each run gets an
isolated `verification-runs/<id>/` directory with input snapshots, rule decks,
tool logs, native `.lyrdb`/`.lvsdb` reports, reusable `settings.json` and `result.json`. The JSON records
input/deck SHA-256 hashes, tool version and enabled parameters. Run again after
editing a design: an older report only describes its own input snapshot.
SPICE must be self-contained; `.include` and `.lib` are refused. The web upload
limits are 20 MiB for GDS and 2 MiB for SPICE.

Input conveniences:

- SKY130 preset and installed-deck readiness; other PDKs are refused rather than
  silently running the wrong deck.
- GDS top-cell names, layer numbers and DBU are inspected automatically. Rule
  layer dropdowns use the uploaded file's actual layers.
- SPICE top-level pins suggest a substrate net such as `VNB`. The input remains
  editable. Use `--substrate VNB` for the public SKY130 standard-cell fixture.
- SPICE dimensions are explicitly selected: SKY130 micron values (`W=0.65`,
  also written `W=650000u` in the public fixture) versus SI (`W=0.65u`). The default
  is micron; `--spice-units si` selects SI. Both conventions are recorded.
- Settings auto-save in the browser, with JSON import/export for reuse and sharing.
  Layout/netlist file contents are not stored in browser preferences.
- Project-specific minimum width, spacing and maximum cell dimensions are
  entered in µm. KLayout checks them through the hierarchy, in addition to the
  unchanged PDK deck. Missing geometry is reported, not silently passed.

Project constraints can also be supplied with `--constraints constraints.json`:

```json
{
  "max_width_um": 100,
  "max_height_um": 100,
  "rules": [
    {"kind": "min_width", "layer": 68, "datatype": 20, "value_um": 0.2},
    {"kind": "min_space", "layer": 68, "datatype": 20, "value_um": 0.2}
  ]
}
```

Upstream decks are downloaded unchanged at pinned revisions, with their license
notices intact and a `sources.json` provenance record:

- [Efabless MPW precheck DRC](https://github.com/efabless/mpw_precheck/blob/0941bdc1b62b5c3f99c8683bd11199d330af2ef3/checks/tech-files/sky130A_mr.drc), GPLv3 notice in the deck.
- [Efabless SKY130 LVS](https://github.com/efabless/sky130_klayout_pdk/blob/dace518392e9f0e98422359cc7063cd4e281b564/tech/sky130/lvs/sky130.lvs), Apache-2.0 notice in the deck.
- [Efabless clear-area metal density](https://github.com/efabless/mpw_precheck/blob/0941bdc1b62b5c3f99c8683bd11199d330af2ef3/checks/drc_checks/klayout/met_min_ca_density.lydrc).

DRC explicitly enables FEOL, BEOL, off-grid and floating-metal checks because
upstream defaults disable several groups. A missing/unreadable result, timeout,
empty LVS comparison, or extraction with no devices cannot pass. The cell review
gate requires DRC/LVS plus any configured project constraints. `--scope chip`
adds density, ERC and antenna to the checklist. The public density deck checks
clear-area density and requires a nonempty chip boundary on GDS 235/4; it does
not represent every density requirement. Process ERC has no qualified backend;
antenna runs when the Magic option is enabled. Missing checks block the chip
gate. This is a physical-verification workflow,
**not foundry sign-off certification**: `signoff.eligible` remains false even
when a cell is `ready_for_review`. Timing, reliability and extraction qualification
remain project-specific requirements.

Actual-engine regression tests use a pinned public SKY130 inverter. Fetch the
fixture and set the application path to include them in the test suite:

```powershell
.venv/Scripts/python.exe tools/fetch_verification_decks.py --fixtures
$env:KLAYOUT_EXE = (Resolve-Path .tools/klayout/klayout-0.30.12-win64/klayout_app.exe).Path
.venv/Scripts/python.exe -m pytest tests/test_verification_integration.py
```

These test clean DRC/LVS, an added narrow wire, mismatched transistor width,
missing chip boundary and excessive metal density. An optional browser test
in `tests/test_verification_browser.py` uses Playwright and `VERIFICATION_BROWSER`
(the path to a Chromium/Edge executable) to verify real uploads, automatic input
suggestions, settings import/export, constraints, persistence and mobile layout.

The SKILL mock also supports `dbCopyFig(figure destination [transform])` and
`dbMoveFig(figure destination [transform])` for geometry and instances. Transforms
support offsets and all eight orthogonal orientations; shape scaling is supported.
Instance magnification and cross-cell moves of connected shapes are explicitly
refused. Copies duplicate geometry without duplicating electrical pins/nets.

`mock_virtuoso` itself has no dependency on `virtuoso_bridge` and never
will — see "Design" below. To run the contract test suite (the tests that
drive the real bridge client and builders against this mock), install
`virtuoso-bridge-lite` as an editable package into the same virtualenv.
This is a test-time-only, developer-machine install; it is intentionally
**not** declared in `pyproject.toml`:

```bash
uv pip install --python .venv/bin/python -e ../virtuoso-bridge-lite
```

## Usage

Start the server:

```bash
mock-virtuoso serve --port 65432
```

Point a `virtuoso-bridge-lite` client at it:

```python
from virtuoso_bridge import VirtuosoClient

client = VirtuosoClient.local(port=65432)
client.execute_skill("1+2")   # VirtuosoResult(status=SUCCESS, output='3')
```

`VirtuosoClient.local(port=...)` is also how the test suite drives the
mock: `MockVirtuosoServer` is used as a context manager bound to port `0`
(the OS picks a free port), and the client connects to `server.port`.

### In a container

```bash
docker build -t mock-virtuoso .
docker run --rm -p 65432:65432 -v ~/.virtuoso-bridge:/token \
    --user "$(id -u):$(id -g)" mock-virtuoso
```

The mounted directory is how the client on the host and the daemon in the
container share one token (see [Bridge token authentication](#bridge-token-authentication));
`--user` keeps the 0600 file readable by you. For the tokenless legacy wire,
mount nothing and pass `-e RB_ALLOW_UNAUTHENTICATED=1
-e RB_TOKEN_PATH=/dev/null/bridge_token` — as with the real daemon, the opt-out
applies only when no token file can be had. Artifacts such as screenshots land
in `/artifacts`. The build copies the source and downloads nothing, so it also
works behind a TLS-inspecting proxy. `docker run --rm mock-virtuoso eval '1+2'`
runs the interpreter one-shot.

## Tests

```bash
pytest                            # unit tests (no bridge dependency)
uv pip install --python .venv/bin/python -e ../virtuoso-bridge-lite
pytest tests/contract             # contract tests (bridge required)
```

Everything under `tests/contract/` is the *only* place in this repository
allowed to import `virtuoso_bridge`. Those tests use
`pytest.importorskip("virtuoso_bridge")` so the suite still collects and
passes (by skipping) on a machine where the bridge isn't installed; install
it as shown above to actually exercise them.

The contract tests drive the real `virtuoso_bridge.VirtuosoClient` over a
real TCP socket against `MockVirtuosoServer`, using the bridge's own SKILL
builders (`virtuoso_bridge.virtuoso.layout.ops`) to generate the SKILL and
the bridge's own reader
(`virtuoso_bridge.virtuoso.layout.reader.parse_layout_geometry_output`) to
parse the results — the only test layer in this project that proves the
mock is useful for its actual purpose, rather than merely internally
consistent.

## Before committing

```bash
git config core.hooksPath .githooks
```

`.githooks/pre-commit` runs the suite and refuses a commit while it is red.
Three commits in one session went in with a failing test — each time the run
happened, printed `1 failed`, and was read as though it said passed. A machine
reads it correctly. `SKIP_TESTS=1` overrides it for the case where the red test
is the point.

## Design

See the design document at
[`../claudedocs/specs/2026-09-21-mock-virtuoso-design.md`](../claudedocs/specs/2026-09-21-mock-virtuoso-design.md).

One deliberate design rule worth calling out: an unsupported/unimplemented
SKILL function raises `unknown function: X` (surfaced to the client as a
NAK / `ExecutionStatus.ERROR`), rather than silently returning `nil`. A
real Virtuoso would do the latter for many unbound symbols in some
contexts, but a silent `nil` here would let missing mock coverage pass as
a false negative — a test asserting `nil` for the "not implemented" path
would keep passing forever, hiding the gap. Loud failure was chosen over
fidelity to that particular Virtuoso quirk.

## Demo

A runnable end-to-end demonstration lives in `demo/demo_layout_session.py`. It drives
`virtuoso-bridge-lite`'s own high-level Python API — `client.layout.edit()`,
`client.open_window()`, `client.get_current_design()`, `client.list_windows()`,
`client.fetch()`, `client.screenshot()` — against the mock. No line in it touches the
mock directly; every call is the same one you would make against a real Cadence Virtuoso.

```bash
uv pip install --python .venv/bin/python -e ../virtuoso-bridge-lite   # test-time only
.venv/bin/python demo/demo_layout_session.py
```

It builds a small layout (device rectangles, metal routing, a via, pin labels), places
two instances of it in a top cell, reads the result back through the bridge's own
`parse_layout_geometry_output`, batch-fetches attributes, writes a screenshot, and shows
unimplemented SKILL (`mae*`, `schCreate*`) failing loudly rather than silently succeeding.

## Driving it with an agent

`virtuoso-bridge-lite` ships agent skills in its `skills/` directory. Because the bridge
already supports a **local mode** — tunnel state `mode: "local"` connects straight to
`127.0.0.1:<port>` with no SSH — the mock can sit exactly where a local Virtuoso would,
and the CLI, the Python API and those skills all work unmodified.

```bash
.venv/bin/python demo/agent_sandbox.py --port 65432     # mock + local-mode bridge state
.venv/bin/virtuoso-bridge status                        # [daemon] OK - connected to Virtuoso CIW
.venv/bin/virtuoso-bridge eval '1+2'                    # {"status": "success", "output": "3"}
```

Point an agent at `virtuoso-bridge-lite/skills/virtuoso/SKILL.md` and give it a design
task. One was asked to build a 2-input NAND standard cell and a three-wide row, told
only to follow the skill and to verify its work by reading the design back. It did,
and its output checks out through the CLI:

```
NAND2 bBox : ((-0.2 0.0) (4.2 4.2))   13 shapes
             NW×1  AA×2  PO×2 + labels A,B   M1×3 (VDD/VSS rails, Y strap) + labels Y,VDD,VSS
ROW        : I0 NAND2 R0 ((-0.2 0.0) (4.2 4.2))
             I1 NAND2 MY ((-0.2 0.0) (4.2 4.2))   <- mirrored, lands back on the same span
             I2 NAND2 R0 (( 7.8 0.0) (12.2 4.2))
```

`demo/agent_sandbox.py` removes the tunnel-state file on exit, so the bridge stops
believing a local Virtuoso is present once you stop the sandbox.

## The introduction panel

The floor carries an **ⓘ About / 소개** button opening a panel that says:
what the mock is, how a request reaches it, what this particular screen does,
what it deliberately does not do, and why it refuses rather than returning nil.

`toolkit/static/about.js` holds it, with a paragraph and a flow line per
screen — a table entry, so a second screen would cost an entry rather than a
rewrite. Korean and English sit side by side in one table
rather than in two files, so editing one language is visibly editing the other
— and a test fails if an entry ever carries only one. The choice is remembered
per browser and defaults to the browser's own language.

## The technology

Small and fixed, but real — the mock refuses anything outside it rather than
drawing something a technology could not produce.

| | |
|---|---|
| layers (purpose `drawing`) | `nwell` `diff` `poly` `met1` `met2` `met3` `text` |
| via definitions | `DIFF_M1` `PO_M1` `M1_M2` `M2_M3` |

`techGetTechFile(cv)` returns the technology, `techFindViaDefByName` answers
`nil` for a name it does not have, as Virtuoso does, and `dbCreateVia` refuses
anything that is not one of these — naming the ones that exist, so a refusal
tells you what would have worked.

## The front end

One screen: the **Agent Design Floor** at `http://127.0.0.1:8900`.

```bash
.venv/bin/python floor/design_floor.py
```

It is where you say what you want, where agents work, and where you watch both.
The request box takes a sentence — Korean or English — and runs it through the
same pipeline the OpenAI server exposes: plan, validate, build, read back. A
request builds through its own lane, so the SKILL it sends lands in the
transcript beside the agents', and the answer comes from the database rather
than from the plan.

The canvas is `toolkit/static/render.js`, the reader `toolkit/layout_reader.py`
and the pipeline `toolkit/planner.py` — all shared with `hermes/`, which is the
same capability with an OpenAI API instead of a screen.

An earlier build had a second front end, a hand-driven Layout Workbench. It was
retired: two screens meant two design databases and two of every helper, and
nothing it did could not be said in words to this one.

## Bridge token authentication

The daemon the bridge ships authenticates every request, and so does this mock.
`src/mock_virtuoso/auth.py` implements wire protocol v1 as
`ramic_bridge_daemon_3.py` defines it: a shared 0600 token file that never
crosses the wire, an HMAC over the *complete* request (so no field can be
swapped in flight), separate MAC domains for the capability handshake and for
execution, signed replies — error replies included, so a squatter on the port
cannot hide behind one — and server-side nonce replay rejection that fails
closed at capacity.

Both ends read the same file, `~/.virtuoso-bridge/bridge_token` by default
(`RB_TOKEN_PATH` for the daemon, `VB_BRIDGE_TOKEN` for the client), creating it
if absent. `MockVirtuosoServer` therefore authenticates by default, as the real
daemon does. The bundled entry points take a different route to the same place:
they hand the mock whatever token their client holds, so a bridge old enough to
predate token auth still gets the wire it expects without any version sniffing.

```python
server = MockVirtuosoServer(session)              # port bound, not yet serving
client = VirtuosoClient.local(port=server.port)
server.auth = Authenticator(getattr(client, "daemon_token", None))
server.start()
```

The contract suite runs whichever wire the installed bridge speaks, and one of
its tests asserts the two agree — a bridge with token auth must be exercising
the authenticated path, not quietly falling back to the legacy one.

## Agent design floor (`floor/`)

`floor/design_floor.py` puts several agents to work in **one** design database and
makes the process watchable:

```bash
.venv/bin/python floor/design_floor.py     # then open http://127.0.0.1:8900
```

One mock holds the design, the way one CIW session would. Each agent gets a *lane* —
a recording proxy standing where the daemon's port would be — and drives it with the
shipped CLI, unmodified:

```bash
echo 'mockCapabilities()' | python tools/floor_skill.py --env floor/lanes.env -p cells --stdin
```

`lanes.env` is generated at startup and simply points each bridge profile at its
lane's port (`VB_REMOTE_HOST_<lane>=localhost`), so the CLI resolves local mode
exactly as it would against a local Virtuoso. Nothing about the agent's tooling is
special-cased for the mock.

Five lanes ship: `cells` and `analog` draw leaf cells, `power` straps the row on
met3, `top` floorplans and places instances, and `verify` draws nothing — it
reads the finished design back and checks the other agents' claims against it.

Each session leaves a knowledge base behind. `floor/harvest.py` reads the
transcript, groups the failures, and matches them against the cases in
`skills/design-floor/kb/` — what it cannot match is what nobody has written
down yet. A case records what was tried, what came back and why, then names the
rule it produced and where that rule now lives, and a test checks the rule is
really there. A lesson cannot quietly fall out of a skill while a case goes on
claiming it.

**And the cases reach the planner.** For a long time they did not: eighteen
cases sat on disk while every request in words was planned cold, free to repeat
a mistake this repository had written down, tested, and in one case written
down twice. `toolkit/precedent.py` closes that, in two directions:

- **before planning** — the standing lessons go into the system prompt. Only
  cases marked `audience: planner` do: most teach an agent writing SKILL by
  hand (`foreach` cannot count, a bare name is a variable) and would be noise
  in a prompt that emits JSON ops. A block nobody finishes reading teaches
  nothing.
- **after a refusal** — `validate` already said exactly what was wrong, and
  that sentence used to go only to the user, as the reason nothing was built.
  It now goes back to the model once, carrying the cases whose `signature`
  matches that error, each cited by id so the citation can be checked. Asked
  for a power grid on `met7`, the planner is refused, told which layers exist,
  and returns met2/met3 — one round trip instead of a dead end.

Retrying is safe there in a way retrying a bridge error would not be:
validation runs before a single op executes, so a refused plan leaves the
design untouched. Bridge failures stay final.

Retrieval is a regex over recorded signatures, not similarity over prose. The
corpus is small and its failures are labelled by the tools themselves, so exact
matching is more precise, needs no model, index or dependency, and can say
*why* a case came back. The idea and its argument are lifted from
`ppa-eda-agent/pipeline/case_retrieval.py`, which had named the same gap in its
own first paragraph.

The first ten cases came from one five-lane session: 112 calls, 27 failures, 11
distinct. The largest single group — 11 of the 27 — was one bad error message in
the mock, which had also produced two confidently wrong conclusions about the
tool in agents' reports. Three cases record successes, including the one where
an agent refused to size a power grid against a cell that was still empty.

Each lane's brief is a file rather than a prompt. `skills/design-floor/SKILL.md`
holds what every agent on the floor needs — how to reach the session, the
technology, the house rules — and `roles/<lane>.md` holds that lane's job. An
agent is dispatched by being told its lane and pointed at those two files. A
test pairs the lanes against the briefs, so adding one without the other fails
rather than leaving an agent with nothing to read.

The observatory at `:8900` shows three things side by side: which agent is doing
what, the full SKILL transcript with every reply, and the layout redrawn from the
database as it grows. Recording happens **on the wire**, not inside the mock —
`mock_virtuoso` is imported only to start the daemon — so the transcript is exactly
what a real Virtuoso would have received. The observatory reads the database
through its own direct connection, which keeps its polling out of the agents'
transcript.

## Natural-language API (`hermes/`)

`hermes/virtuoso_api_server.py` is an **OpenAI-compatible** server that turns a plain
request into a real layout:

```bash
.venv/bin/python hermes/virtuoso_api_server.py --port 8750
curl http://127.0.0.1:8750/v1/chat/completions -H 'Content-Type: application/json' -d '{
  "model":"virtuoso-fde",
  "messages":[{"role":"user","content":"STDLIB에 NAND2 셀을 정의하고 ROW에 4개 배치해줘"}]}'
```

Pipeline: request → planner → **validation** → `virtuoso-bridge-lite` builders → mock →
read back → answer.

The planner is pluggable. `--planner hermes` asks a hermes-agent OpenAI server for a JSON
plan (that model does not do OpenAI tool-calling, so it plans in JSON and this server
executes); `--planner rules` is a deterministic parser that needs no LLM at all;
`auto` prefers hermes and falls back.

**It uses a gateway of its own.** This project has a hermes profile named
`virtuoso-bridge` (gateway on `:8650`), and the planner now prefers it over every other
profile. Start it once and discovery does the rest:

```bash
~/.hermes/hermes-agent/venv/bin/python -m hermes_cli.main \
  --profile virtuoso-bridge gateway run
.venv/bin/python floor/design_floor.py
```

Finding it took two fixes. The planner hardcoded one port, so a gateway on any other
port was invisible. Worse, **each profile carries its own key**: probing ports with the
one key in `~/.hermes/.env` got a 401 from the dedicated gateway, which to the caller
looks exactly like a port with nobody on it — so the planner walked past the server
built for this job and used whichever profile happened to answer. Keys now come from the
same profile directory as the port, and a profile's `.env` outranks its config `token`
where the two disagree, because the running gateway honours `.env`.

To override all of that, pin it:

```bash
VB_PLANNER_URL=http://127.0.0.1:8650 VB_PLANNER_MODEL=virtuoso-bridge \
  VB_PLANNER_KEY=<that gateway's key> .venv/bin/python floor/design_floor.py
```

Unset, the planner walks the profiles (preferred one first), asks each `/v1/models` what
it actually serves, and falls back to a short list of bare ports. Nothing reachable is a
stated reason, not a silent downgrade to the rules planner.

Two properties worth stating plainly:

The shared Hermes harness repairs malformed or truncated JSON and invalid plan
fields before execution. A repair receives the original request, the rejected plan,
the validation error and relevant recorded lessons. It is bounded to one planning
retry and one DRC correction by default; bridge execution failures are not blindly
retried. A correction with missing readback or an unavailable DRC check cannot
replace the previous design. `--planner hermes` refuses an unavailable model instead
of substituting the rules template; `auto` retains its explicit template fallback.

Design Floor responses include `harness`, and the OpenAI-compatible endpoint returns
it under `x_virtuoso.harness`: attempt stage, outcome, elapsed time, DRC error count,
readback errors and final verification status. These refer to mockTech checks,
not SKY130 or foundry sign-off. Attempt metadata does not contain API keys or prompts.

Run a reproducible recovery evaluation:

```powershell
.venv/Scripts/python.exe tools/evaluate_harness.py --repeats 3
.venv/Scripts/python.exe tools/evaluate_harness.py --live --output .tools/harness-live.json
```

Replay compares retries disabled/enabled across clean, malformed JSON, malformed
coordinates, truncated, DRC-failing and persistently invalid responses. Only model
responses are replayed: HTTP, bridge execution, database readback and mockTech DRC
are real. The independent task check requires one rectangle at the requested
coordinates; an empty design or fallback cannot pass. The JSON report records every
trial, model-call counts (replay), elapsed time and aggregate task success counts.
This is a repair ablation, not a measured before/after improvement in model quality.
`--live` uses `VB_PLANNER_URL`, `VB_PLANNER_MODEL` and `VB_PLANNER_KEY` (or profile
discovery) for a narrow live rectangle task; it fails if no model is available.

**The model's output is never executed.** Every plan passes a strict validator first —
op whitelist, layer whitelist, numeric coordinates with bounds, identifier-only cell and
instance names, a plan-size cap. Injection attempts like a cell named
`C") dbDeleteObject(cv) ("` or a coordinate of `0; dbDeleteObject(cv)` are rejected
before anything reaches the bridge, and a validated op with no builder raises rather than
being skipped.

**The answer is grounded in the database, not the plan.** After executing, the server
reads the design back through the bridge's own reader and reports the actual per-layer
counts, bounding boxes and instance transforms. If a plan instantiates a cell it never
defined, the reply says so instead of returning an empty box.

## Known upstream issues

While building the contract tests (Task 12), we found that
`virtuoso_bridge.virtuoso.layout.ops.layout_read_summary` emits SKILL whose
`return(buf)` sits **inside** the body of `foreach(inst cv~>instances ...)`
instead of after the loop:

```
foreach(inst cv~>instances buf = strcat(...) return(buf)))
```

In SKILL, `return()` unwinds the enclosing `prog`, so this has two
consequences, both reproduced against the mock and pinned by
`tests/contract/test_layout_contract.py`:

- **Zero instances**: the `foreach` body never runs, so `return` never
  executes, and the whole function evaluates to `nil` instead of the
  expected summary string.
- **One or more instances**: the function returns after the *first*
  `foreach` iteration. The header line correctly reports the true instance
  count (e.g. `3 instances`), but the body lists only the first instance.

`layout_read_geometry` does not have this bug — it builds its output
string outside the loop and lists every shape/instance.

`mock-virtuoso` faithfully executes the SKILL it is given, including this
bug; that is the mock behaving correctly, not a defect in the mock. The
fix belongs in `virtuoso-bridge-lite` (a separate repository) and is out
of scope here — `mock-virtuoso` must not special-case around it. If
`layout_read_summary` is fixed upstream, the two contract tests
(`test_read_summary_upstream_bug_zero_instances_yields_nil` and
`test_read_summary_upstream_bug_truncates_after_first_instance`) will fail
and must be flipped to match the corrected behavior.

## Verified SKY130 comparator

A separate `layout_gen/strongarm_sky130` demonstrator preserves the original
conceptual comparator and provides real SKY130 device geometry, an independent
reference schematic, DRC/LVS/antenna checks, RC extraction and paired reference /
post-layout ngspice characterization. See
[the comparator workflow](comparator-sky130/README.md) and
[its measured evidence summary](comparator-sky130/summary.json) for exact inputs,
conditions, tool versions, limitations and reproduction commands.
