"""The bundled tools import virtuoso-bridge, so their tests skip without it.

They also live outside the installed package, so the repository root goes on
sys.path to reach `hermes/` and `floor/` the way running the scripts does.
"""

import sys
from pathlib import Path

import pytest

pytest.importorskip(
    "virtuoso_bridge",
    reason="virtuoso-bridge-lite must be installed to test the bundled tools",
)

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
