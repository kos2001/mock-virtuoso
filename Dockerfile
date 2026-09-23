# mock-virtuoso as a container: the daemon, and nothing the wheel does not ship.
#
#   docker build -t mock-virtuoso .
#   docker run --rm -p 65432:65432 -v ~/.virtuoso-bridge:/token \
#       --user "$(id -u):$(id -g)" mock-virtuoso
#
# The bridge client on the host reads the same token file the daemon signs with,
# so mount the host's ~/.virtuoso-bridge at /token; --user keeps the 0600 file
# readable by you. Like the real daemon, the opt-out applies only when no token
# file can be had, so the tokenless legacy wire needs both:
#   -e RB_ALLOW_UNAUTHENTICATED=1 -e RB_TOKEN_PATH=/dev/null/bridge_token
#
# The package is pure stdlib with no dependencies, so the build copies the
# source and fetches nothing — it works behind a TLS-inspecting proxy that the
# base image does not trust, and in CI alike.

FROM python:3.13-slim

RUN useradd --create-home --uid 1000 virtuoso \
 && mkdir -p /token /artifacts \
 && chown virtuoso:virtuoso /token /artifacts

COPY src/mock_virtuoso /opt/mock-virtuoso/mock_virtuoso

USER virtuoso
ENV PYTHONPATH=/opt/mock-virtuoso \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    RB_TOKEN_PATH=/token/bridge_token
VOLUME ["/token", "/artifacts"]
EXPOSE 65432
# serve stops on SIGINT (Ctrl-C); as PID 1 it would otherwise ignore SIGTERM
# and `docker stop` would wait out its timeout and kill it.
STOPSIGNAL SIGINT
ENTRYPOINT ["python", "-m", "mock_virtuoso.cli"]
CMD ["serve", "--host", "0.0.0.0", "--port", "65432", "--artifact-dir", "/artifacts"]
