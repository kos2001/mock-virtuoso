# Working on mock-virtuoso

For bridge-driven layout or circuit work, read `skills/design-floor/SKILL.md`
and its `references/bridge-workflow.md`. An assigned lane also has a brief in
`skills/design-floor/roles/`. Do not assume the bridge's entire Cadence API is
implemented by this mock. Python bridge availability is not backend capability.

Use the repository virtual environment. On Windows its executables are in
`.venv/Scripts`; on POSIX they are in `.venv/bin`. The installed bridge checkout
may be under `.tools/virtuoso-bridge-lite`; inspect its actual version and docs.
Do not copy its broad real-Cadence instructions into the mock unconditionally.

For changes to SKILL behavior, run the relevant domain tests and
`tests/contract` against the installed bridge. For skill guidance, also run
`tests/test_design_floor_skills.py` and `tests/test_design_floor_kb.py`.
Contract tests use an isolated server; do not exercise destructive examples
against the user's live design. Preserve unrelated working-tree changes.

Report mock checks, external tool checks and foundry-qualified sign-off
separately. Record the exact target, input revision/hash, rules/PDK, tool,
status and artifact paths for any external verification claim. A missing tool,
failed invocation or stale report cannot establish a pass.
