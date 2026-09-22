"""Keep the suite off the developer's real bridge token.

Both the mock (as the daemon) and virtuoso-bridge (as the client) read a
shared token file, defaulting to ~/.virtuoso-bridge/bridge_token and creating
it if absent. A test run must not create, read or re-permission the real one,
so both ends are pointed at a file inside the run's own temp directory. They
still have to agree, which is the property the contract tests depend on.
"""

import os

import pytest

from mock_virtuoso.auth import TOKEN_PATH_ENV

CLIENT_TOKEN_PATH_ENV = "VB_BRIDGE_TOKEN"   # virtuoso_bridge.daemon_auth


@pytest.fixture(scope="session", autouse=True)
def isolated_bridge_token(tmp_path_factory):
    token_file = tmp_path_factory.mktemp("bridge-token") / "bridge_token"
    previous = {}
    for name in (TOKEN_PATH_ENV, CLIENT_TOKEN_PATH_ENV):
        previous[name] = os.environ.get(name)
        os.environ[name] = str(token_file)
    yield token_file
    for name, value in previous.items():
        if value is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = value
