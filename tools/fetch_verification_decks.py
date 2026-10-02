"""Download pinned upstream SKY130 decks, preserving source and license notices."""
import hashlib
import json
import argparse
from pathlib import Path
from urllib.request import urlopen

SOURCES = {
    "sky130.drc": ("efabless/mpw_precheck", "0941bdc1b62b5c3f99c8683bd11199d330af2ef3",
                   "checks/tech-files/sky130A_mr.drc"),
    "sky130.lvs": ("efabless/sky130_klayout_pdk", "dace518392e9f0e98422359cc7063cd4e281b564",
                   "tech/sky130/lvs/sky130.lvs"),
    "density.lydrc": ("efabless/mpw_precheck", "0941bdc1b62b5c3f99c8683bd11199d330af2ef3",
                      "checks/drc_checks/klayout/met_min_ca_density.lydrc"),
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixtures", action="store_true", help="Also download the public SKY130 inverter integration fixture")
    args = parser.parse_args()
    target = Path(__file__).resolve().parents[1] / ".tools" / "sky130"
    target.mkdir(parents=True, exist_ok=True)
    manifest = {}
    for name, (repo, revision, path) in SOURCES.items():
        url = f"https://raw.githubusercontent.com/{repo}/{revision}/{path}"
        with urlopen(url, timeout=60) as response:
            data = response.read()
        (target / name).write_bytes(data)
        manifest[name] = {"url": url, "revision": revision,
                          "sha256": hashlib.sha256(data).hexdigest()}
    (target / "sources.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(target)
    if args.fixtures:
        fixture = target.parent / "sky130-fixture"
        fixture.mkdir(exist_ok=True)
        base = "https://raw.githubusercontent.com/google/skywater-pdk-libs-sky130_fd_sc_hd/ac7fb61f06e6470b94e8afdf7c25268f62fbd7b1/"
        provenance = {}
        for path in ("cells/inv/sky130_fd_sc_hd__inv_1.gds",
                     "cells/inv/sky130_fd_sc_hd__inv_1.spice", "LICENSE"):
            with urlopen(base + path, timeout=60) as response:
                data = response.read()
            name = Path(path).name
            (fixture / name).write_bytes(data)
            provenance[name] = {"url": base + path, "sha256": hashlib.sha256(data).hexdigest()}
        (fixture / "sources.json").write_text(json.dumps(provenance, indent=2), encoding="utf-8")
        print(fixture)


if __name__ == "__main__":
    main()
