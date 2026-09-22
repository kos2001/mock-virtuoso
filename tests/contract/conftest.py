"""계약 테스트 픽스처.

이 디렉터리의 테스트만 virtuoso_bridge를 import한다. mock_virtuoso 자체는
브릿지를 절대 의존하지 않는다 (스펙 §4).
"""

from __future__ import annotations

import pytest

from mock_virtuoso.bridge_compat import match_client_auth
from mock_virtuoso.server import MockVirtuosoServer
from mock_virtuoso.session import Session


def _match_client_auth(mock, client) -> None:
    """Give the mock whatever bridge token this client holds.

    Token auth arrived in the bridge partway through this project's life. Rather
    than sniff versions, the daemon adopts the client's secret: a client new
    enough to carry one gets an authenticated daemon sharing it, and an older
    tokenless client gets the legacy wire it expects. Both ends agree by
    construction, which is not something a version check can promise -- and
    whichever wire is installed is the one these tests exercise for real.
    """
    match_client_auth(mock, client)


@pytest.fixture
def bridge_client(tmp_path):
    pytest.importorskip(
        "virtuoso_bridge",
        reason="virtuoso-bridge-lite must be installed for contract tests",
    )
    from virtuoso_bridge import VirtuosoClient

    session = Session(artifact_dir=tmp_path)
    # The port is bound by the constructor but nothing is served until start(),
    # so the client can be built -- and its token adopted -- in between.
    server = MockVirtuosoServer(session)
    client = VirtuosoClient.local(port=server.port)
    _match_client_auth(server, client)
    server.start()
    try:
        yield client, session
    finally:
        server.stop()
