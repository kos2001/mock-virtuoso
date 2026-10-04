# SKY130 StrongARM comparator verification

`layout_gen/strongarm_sky130/layout` is a new 11-transistor demonstrator built
with the installed SKY130 Magic generators. The original conceptual
`strongarm_comparator` is preserved. Its historical schematic was unavailable;
`reference.spice` declares the new independent reference and port ordering.
VINP > VINN produces OUTP high and OUTN low during CLK high. CLK low precharges
both outputs. Each MOS has L=0.15 um; W is declared in the reference.

The generated layout has real implant, tap, LI, contact, metal and via layers.
The generator uses the 0.005 um manufacturing grid explicitly; GDS precision
is 0.001 um. Its placement and generous routing target verifiable connectivity,
not optimized comparator matching or minimum area.

`summary.json` records the exact physical run, input hashes, pinned PDK revision,
tool versions, geometry readback and measured simulation results. The matching
native DRC/LVS/Magic artifacts are in the referenced `verification-runs` folder.
`roundtrip.json` records zero physical polygon XOR for all layers after importing
into the live mock database and exporting again. `layout-preview.png` is the
checked browser view; a screenshot alone is not electrical verification.

Simulation uses real ngspice with pinned SKY130 models at tt/ff/ss/fs/sf and
-40/27/125 C, with +/-10 mV differential input, 0.9 V common mode, 1.8 V supply,
10 MHz clock and 5 fF on each output. There are three decisions per case.
The functional criterion is correct polarity with at least 80% VDD differential
before the end of the evaluation window. Reset is checked one ns before each
rising edge. Delay is measured from CLK's 50% edge to that output threshold,
with a maximum time step of 20 ps. Reported power uses only DUT VDD current
averaged over 100-300 ns and excludes ideal clock/input driver energy.
Additional TT/27 C cases alternate input polarity on successive cycles.

Magic's native `.subckt extracted` has named electrical nets but no GDS port
flags. `characterize.py` exposes its seven existing named nets as ports of the
simulation DUT. This changes no MOS, R or C records; native and adapted netlist
hashes are recorded. PEX simulation requires DRC, LVS, extraction and antenna
passes from the same run. `report.py` checks input hashes and raw waveforms
before accepting the aggregate report.

From the repository root, with the local PDK and EDA tools installed:

```sh
.venv/bin/python comparator-sky130/build.py
QT_QPA_PLATFORM=offscreen .venv/bin/python comparator-sky130/verify.py
.venv/bin/python comparator-sky130/import_floor.py
.venv/bin/python comparator-sky130/check_roundtrip.py
.venv/bin/python comparator-sky130/characterize.py
.venv/bin/python comparator-sky130/characterize.py --mode pex
.venv/bin/python comparator-sky130/characterize.py --mode pex --quick --alternating
.venv/bin/python comparator-sky130/report.py
```

The floor scripts connect to the authenticated request lane in
`.tools/layout-check-lanes.env`; they preserve existing cells. Do not rebuild
an edited live cell under the same name without preserving its work.

Performance acceptance limits were not supplied. Voltage sweep, device
mismatch, noise/offset distributions, input common-mode range and maximum
clock-rate characterization are outside these measured cases. Public PDK
DRC/LVS/antenna results do not establish foundry-qualified sign-off.
