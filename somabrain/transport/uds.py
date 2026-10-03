"""Unix-domain-socket binding — the standalone transport.

Same host, one compose network, one mounted directory. gRPC over a Unix socket
skips the TCP/IP stack entirely: the kernel moves the bytes, there is no
loopback interface, no ephemeral port, and no TLS handshake on the hot path.
This is as close to in-process as a container boundary allows.

Security is filesystem permissions, not cryptography. The socket is created
mode 0600 inside ``/run/soma`` and must never be exposed off-host. Because the
kernel already enforces peer identity through the socket inode, no bearer token
is issued or required on this binding — and inventing one here would be a
credential that gates nothing, which is exactly the dummy-credential failure
mode the standing rules forbid.
"""

from __future__ import annotations

import logging
import os
import stat

import grpc

from somabrain.transport.client import BrainClient
from somabrain.transport.port import (
    BRAIN_SOCK,
    RUN_DIR,
    TransportConfigurationError,
)

logger = logging.getLogger("somabrain.transport.uds")

# Owner read+write only. Group/other have no access to the bus.
SOCKET_MODE = 0o600
DIR_MODE = 0o700

# ``sockaddr_un.sun_path`` is a fixed-size buffer: 104 bytes on macOS/BSD and
# 108 on Linux, one of which is the terminating NUL. gRPC's own bind fails with
# "Path name should not have more than 103 characters", so 103 is the ceiling
# on every platform we target — Linux simply allows a little more. Checking
# here turns that opaque bind failure into a named configuration error.
MAX_SOCKET_PATH_LEN = 103


def ensure_run_dir(path: str = RUN_DIR) -> None:
    """Create the shared socket directory with owner-only permissions.

    Args:
        path: Directory that holds the brain and SFM sockets.

    Raises:
        TransportConfigurationError: If the directory cannot be created or its
            permissions cannot be locked down. A world-readable socket bus is a
            cross-tenant read path and is refused rather than tolerated.
    """
    try:
        os.makedirs(path, mode=DIR_MODE, exist_ok=True)
        # makedirs honours the umask, so set the mode explicitly afterwards.
        os.chmod(path, DIR_MODE)
    except OSError as exc:
        raise TransportConfigurationError(
            f"cannot prepare socket directory {path!r}: {exc}"
        ) from exc

    st = os.stat(path)
    if st.st_mode & (stat.S_IRWXG | stat.S_IRWXO):
        raise TransportConfigurationError(
            f"socket directory {path!r} is accessible to group or other "
            f"({oct(st.st_mode & 0o777)}); the local bus must be owner-only "
            f"({oct(DIR_MODE)})"
        )


def check_socket_permissions(path: str) -> None:
    """Verify the peer socket is owner-only before connecting.

    Args:
        path: Path to the peer's Unix socket.

    Raises:
        TransportConfigurationError: If the socket is missing, is not a socket,
            or is readable or writable by group or other.
    """
    if not os.path.exists(path):
        raise TransportConfigurationError(
            f"brain socket {path!r} does not exist. Start SomaBrain, or set "
            "SA01_DEPLOYMENT_MODE=NET to reach it over TCP/TLS instead."
        )
    st = os.stat(path)
    if not stat.S_ISSOCK(st.st_mode):
        raise TransportConfigurationError(
            f"{path!r} exists but is not a socket (mode {oct(st.st_mode)}); "
            "refusing to connect"
        )
    if st.st_mode & (stat.S_IRWXG | stat.S_IRWXO):
        raise TransportConfigurationError(
            f"brain socket {path!r} is accessible to group or other "
            f"({oct(st.st_mode & 0o777)}); the local bus must be mode "
            f"{oct(SOCKET_MODE)}"
        )


def socket_target(path: str = BRAIN_SOCK) -> str:
    """Return the gRPC target string for a Unix socket path.

    gRPC names a Unix socket as ``unix://<absolute path>`` — the path keeps its
    leading slash, so ``/run/soma/brain.sock`` becomes
    ``unix:///run/soma/brain.sock``.

    Raises:
        TransportConfigurationError: If the path is relative or longer than the
            kernel's ``sun_path`` buffer allows. A path that is too long fails
            deep inside gRPC's bind; it is refused here instead, where the
            offending value is still in hand.
    """
    if not path.startswith("/"):
        raise TransportConfigurationError(
            f"Unix socket path must be absolute, got {path!r}"
        )
    if len(path) > MAX_SOCKET_PATH_LEN:
        raise TransportConfigurationError(
            f"Unix socket path is {len(path)} characters, which exceeds the "
            f"{MAX_SOCKET_PATH_LEN}-character ``sun_path`` limit "
            f"({path!r}). Shorten the directory; the kernel cannot bind it."
        )
    return f"unix://{path}"


def build_channel(path: str = BRAIN_SOCK) -> grpc.aio.Channel:
    """Open a gRPC channel to the brain over a Unix socket.

    Args:
        path: Absolute path to the brain's socket.

    Returns:
        A connected ``grpc.aio.Channel``.

    Raises:
        TransportConfigurationError: If the socket is absent, is not a socket,
            or has permissions wider than 0600.
    """
    check_socket_permissions(path)
    target = socket_target(path)
    logger.debug("brain transport: UDS channel to %s", target)
    return grpc.aio.insecure_channel(target)


def build_client(
    path: str = BRAIN_SOCK, *, deadline_s: float | None = None
) -> BrainClient:
    """Build a working :class:`BrainClient` bound to the local Unix socket.

    Args:
        path: Absolute path to the brain's socket.
        deadline_s: Per-call deadline override.

    Returns:
        A ready :class:`BrainClient`.

    Raises:
        TransportConfigurationError: If the socket bus is not usable.
    """
    channel = build_channel(path)
    kwargs = {} if deadline_s is None else {"deadline_s": deadline_s}
    return BrainClient(channel, **kwargs)


def enforce_socket_mode(path: str = BRAIN_SOCK) -> None:
    """Force the bound socket to ``SOCKET_MODE`` and verify it stuck.

    gRPC creates the Unix socket with the process umask, which normally yields
    0755 — a world-readable bus. That is a cross-tenant read path, so the mode
    is corrected immediately after bind and then re-read from the inode to
    confirm. This is called by :func:`start_local_server`; anything that binds
    a socket by hand must call it too.

    Args:
        path: Absolute path to the bound socket.

    Raises:
        TransportConfigurationError: If the socket is absent, or if its mode
            cannot be reduced to owner-only.
    """
    if not os.path.exists(path):
        raise TransportConfigurationError(
            f"cannot set socket permissions: {path!r} was not created"
        )
    try:
        os.chmod(path, SOCKET_MODE)
    except OSError as exc:
        raise TransportConfigurationError(
            f"cannot restrict socket {path!r} to {oct(SOCKET_MODE)}: {exc}"
        ) from exc

    st = os.stat(path)
    mode = stat.S_IMODE(st.st_mode)
    if mode != SOCKET_MODE:
        raise TransportConfigurationError(
            f"socket {path!r} is at {oct(mode)} after chmod to {oct(SOCKET_MODE)}; "
            "refusing to serve on a bus that is not owner-only"
        )


def listen_address(path: str = BRAIN_SOCK) -> str:
    """The server-side bind address for the local socket.

    The server calls :func:`ensure_run_dir` and creates the socket at
    :data:`SOCKET_MODE` before serving. The path is removed first so a socket
    left behind by a killed process does not make the brain unstartable.
    """
    if not path.startswith("/"):
        raise TransportConfigurationError(
            f"Unix socket path must be absolute, got {path!r}"
        )
    ensure_run_dir(os.path.dirname(path))
    if os.path.exists(path):
        os.unlink(path)
    return f"unix://{path}"


async def start_local_server(
    server: "grpc.aio.Server",
    *,
    path: str = BRAIN_SOCK,
) -> str:
    """Bind ``server`` to the local socket and lock the socket down.

    This is the supported way to bring up the standalone transport. It binds,
    starts, and only then enforces ``SOCKET_MODE`` — the order matters, because
    the inode does not exist until the bind happens.

    Args:
        server: A ``grpc.aio.Server`` with services already registered.
        path: Absolute path to the brain's socket.

    Returns:
        The bound target string.

    Raises:
        TransportConfigurationError: If the socket cannot be created or
            restricted to owner-only. The server is not left running on a bus
            that is too open.
    """
    target = listen_address(path)
    bound = server.add_insecure_port(target)
    if not bound:
        raise TransportConfigurationError(
            f"gRPC failed to bind {target!r}; nothing is listening"
        )
    await server.start()
    try:
        enforce_socket_mode(path)
    except TransportConfigurationError:
        await server.stop(0)
        raise
    return target
