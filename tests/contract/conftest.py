"""계약 테스트 픽스처.

이 디렉터리의 테스트만 virtuoso_bridge를 import한다. mock_virtuoso 자체는
브릿지를 절대 의존하지 않는다 (스펙 §4).
"""

from __future__ import annotations

import pytest

from mock_virtuoso.server import MockVirtuosoServer
from mock_virtuoso.session import Session


@pytest.fixture
def bridge_client(tmp_path):
    pytest.importorskip(
        "virtuoso_bridge",
        reason="virtuoso-bridge-lite must be installed for contract tests",
    )
    from virtuoso_bridge import VirtuosoClient

    session = Session(artifact_dir=tmp_path)
    with MockVirtuosoServer(session) as server:
        client = VirtuosoClient.local(port=server.port)
        yield client, session
