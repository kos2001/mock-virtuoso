"""Install pinned SKY130 primitives and Magic into .tools through WSL Ubuntu.

Use --system-deps once to install build packages in the WSL distribution.
The application itself continues to run on Windows, on the existing port.
"""
import argparse
import json
from pathlib import Path
import subprocess

PDK = "0c1df35fd535299ea1ef74d1e9e15dedaeb34c32"
MAGIC = "4f53bb3091d1e4a9b2009a58f157a8a4331d4c84"
ROOT = Path(__file__).resolve().parents[1]


def linux(path):
    text = Path(path).resolve().as_posix()
    return "/mnt/" + text[0].lower() + text[2:] if text[1:2] == ":" else text


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--distro", default="Ubuntu")
    parser.add_argument("--system-deps", action="store_true")
    args = parser.parse_args()

    def run(command, cwd=ROOT, root=False):
        prefix = ["wsl.exe", "-d", args.distro]
        if root:
            prefix += ["-u", "root"]
        subprocess.run([*prefix, "--cd", linux(cwd), "--exec", *command], check=True)

    if args.system_deps:
        run(["apt-get", "update"], root=True)
        run(["env", "DEBIAN_FRONTEND=noninteractive", "apt-get", "install", "-y",
             "git", "build-essential", "python3-venv", "tcl-dev", "tk-dev", "libx11-dev",
             "libxext-dev", "libxt-dev", "libglu1-mesa-dev", "libncurses-dev"], root=True)
    run(["python3", "-m", "venv", ".tools/ciel-venv"])
    run([".tools/ciel-venv/bin/pip", "install", "ciel==3.0.0"])
    run([".tools/ciel-venv/bin/ciel", "fetch", "--pdk-root", ".tools/pdks-linux",
         "--pdk", "sky130", "-l", "sky130_fd_pr", PDK])
    source = ROOT / ".tools/magic-src"
    if not source.exists():
        run(["git", "clone", "--no-checkout", "https://github.com/RTimothyEdwards/magic.git", ".tools/magic-src"])
        run(["git", "fetch", "--depth", "1", "origin", MAGIC], cwd=source)
        run(["git", "checkout", "--detach", MAGIC], cwd=source)
    # Refuse to silently build a different revision; preserve local source edits.
    actual = subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip()
    if actual != MAGIC:
        raise SystemExit(f"Expected Magic commit {MAGIC}, found {actual}; use a separate source checkout")
    run(["./configure", "--prefix=" + linux(ROOT / ".tools/magic-install")], cwd=source)
    run(["make", "-j4"], cwd=source)
    run(["make", "install"], cwd=source)
    run([linux(ROOT / ".tools/magic-install/bin/magic"), "--version"])
    (ROOT / ".tools/pdk-install.json").write_text(json.dumps({"pdk_revision": PDK,
        "magic_revision": MAGIC, "wsl_distribution": args.distro}, indent=2))


if __name__ == "__main__":
    main()
