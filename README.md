# mock-virtuoso

A test double that speaks the Cadence RAMIC bridge TCP protocol and
interprets a subset of Cadence SKILL, so `virtuoso-bridge-lite` can be
developed and tested without a real Cadence Virtuoso installation.

`mock-virtuoso` listens on a TCP port, accepts the same wire protocol the
real RAMIC bridge daemon (`ramic_bridge_daemon_3.py`) speaks, evaluates the
SKILL it receives against an in-memory design database (cellviews, shapes,
instances, windows, layer/purpose palette), and replies with the same
byte-level success/failure framing the real daemon uses.

## What this is not

This is not an EDA tool. It does not implement DRC, LVS, device physics,
parasitic extraction, simulation, or anything resembling real layout
verification. It implements just enough of SKILL's surface syntax and a
subset of the `db*`/`dd*`/`tech*`/`hi*`/`ge*`/`le*`/`pte*` function families
to let a bridge client create, read back, select, and delete layout
geometry and to exercise the protocol layer. Schematic functions (`sch*`)
and Maestro functions (`mae*`) are out of scope for this milestone; calling
them fails with `unknown function`, which is the same failure mode as
calling any other unimplemented function (see "Design" below).

## Install

```bash
uv venv .venv && source .venv/bin/activate
uv pip install -e ".[dev]"
```

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
