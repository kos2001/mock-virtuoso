"""Code shared by the bundled tools in webapp/, floor/, hermes/ and demo/.

Deliberately outside `src/mock_virtuoso`: everything here talks to
virtuoso-bridge, and the mock package must keep standing on its own without
it. Not shipped in the wheel either — these are programs that drive the mock,
not part of it.
"""
