"""Install the pinned official Windows ngspice distribution inside .tools.

Requires py7zr: python -m pip install py7zr
Source: https://ngspice.sourceforge.io/download.html
"""
from pathlib import Path
import hashlib
import json
import urllib.request

ROOT = Path(__file__).resolve().parents[1] / ".tools"
URL = "https://downloads.sourceforge.net/project/ngspice/ng-spice-rework/47/ngspice-47_64.7z"
SHA256 = "59225971bd68cdd1199443649aa4615a9e6d684933f205ab49006a3942518f5a"


def main():
    import py7zr
    ROOT.mkdir(exist_ok=True)
    archive = ROOT / "ngspice-47_64.7z"
    if not archive.exists():
        with urllib.request.urlopen(URL, timeout=60) as source, archive.open("wb") as dest:
            while chunk := source.read(1024 * 1024):
                dest.write(chunk)
    if hashlib.sha256(archive.read_bytes()).hexdigest() != SHA256:
        raise ValueError("ngspice archive checksum mismatch; remove the incomplete archive and retry")
    target = ROOT / "ngspice"
    target.mkdir(exist_ok=True)
    with py7zr.SevenZipFile(archive) as bundle:
        bundle.extractall(target)
    (target / "source.json").write_text(json.dumps({"url": URL, "sha256": SHA256, "version": "47"}, indent=2), encoding="utf-8")
    print(target / "Spice64" / "bin" / "ngspice_con.exe")


if __name__ == "__main__":
    main()
