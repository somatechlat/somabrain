"""TCP binding — the distributed transport.

Cross-host, scale-out. gRPC over TCP with HTTP/2 (RFC 9113): one multiplexed
connection per peer carries N concurrent recalls as N streams, so 50 in-flight
recalls share one connection instead of opening 50. HTTP/2 also supplies the
flow control and GOAWAY/PING signals (RFC 9113 §6.9, §8.4.1, §8.5) this binding
uses for keepalive and clean teardown.

Confidentiality and integrity come from TLS 1.3 (RFC 8446). Peer certificates
are validated to a configured trust anchor per RFC 5280 §6 with the serverAuth
extended key usage (RFC 5280 §4.2.1.12, id-kp 1.3.6.1.5.5.7.3.1); the channel
refuses to fall back to plaintext and never accepts a certificate it cannot
validate.

Unlike the Unix-socket binding, this one is reachable off-host, so it requires
a real service credential. A missing token is a refusal (VIBE Rule 91): there
is no anonymous path and no placeholder value.
"""

from __future__ import annotations

import logging
from pathlib import Path

import grpc

from somabrain.transport.client import BrainClient
from somabrain.transport.port import TransportConfigurationError

logger = logging.getLogger("somabrain.transport.net")

# gRPC keepalive: detect a dead peer within seconds rather than holding a
# connection to a host that is gone. keepalive_permit_without_calls is left
# False so an idle channel does not ping continuously.
KEEPALIVE_TIME_S = 30
KEEPALIVE_TIMEOUT_S = 10
KEEPALIVE_PERMIT_WITHOUT_CALLS = False

# HTTP/2 concurrent streams per connection. Above this the channel opens
# another connection; at or below it, calls multiplex on the one they have.
MAX_CONCURRENT_STREAMS = 64


def _read_required_file(path: str, what: str) -> bytes:
    """Read a credential file, refusing if it is absent or empty.

    Args:
        path: Filesystem path to the credential.
        what: Description used in the error message.

    Returns:
        The file's bytes.

    Raises:
        TransportConfigurationError: If the file is missing, empty, or
            unreadable. An absent credential is a refusal, never a blank.
    """
    if not path:
        raise TransportConfigurationError(
            f"{what} path is not configured; the NET binding requires it. "
            "Refusing to connect without it."
        )
    p = Path(path)
    if not p.is_file():
        raise TransportConfigurationError(
            f"{what} file {path!r} does not exist. The NET binding refuses to "
            "connect with a missing credential."
        )
    try:
        data = p.read_bytes()
    except OSError as exc:
        raise TransportConfigurationError(
            f"{what} file {path!r} cannot be read: {exc}"
        ) from exc
    if not data.strip():
        raise TransportConfigurationError(
            f"{what} file {path!r} is empty. An empty credential is an absent "
            "credential; refusing to connect."
        )
    return data


def require_service_token(token: str | None) -> str:
    """Return a usable service token or raise.

    Args:
        token: The token value resolved from Vault (or equivalent).

    Returns:
        The token, guaranteed non-empty.

    Raises:
        TransportConfigurationError: If the token is missing or blank. A blank
            string is never treated as "no auth needed" on this binding — that
            is the dummy-credential pattern and it is a security violation.
    """
    if token is None or not str(token).strip():
        raise TransportConfigurationError(
            "NET binding requires a service token and none is configured. "
            "Refusing to connect: an absent credential is a refusal, not a blank."
        )
    return str(token).strip()


def build_channel(
    *,
    host: str,
    port: int,
    server_name: str | None = None,
    ca_file: str | None = None,
    cert_file: str | None = None,
    key_file: str | None = None,
    token: str | None = None,
) -> grpc.aio.Channel:
    """Open a TLS gRPC channel to a remote brain.

    Args:
        host: Peer hostname or IP.
        port: Peer port.
        server_name: Expected name in the peer certificate (SNI / authority
            check). Defaults to ``host``.
        ca_file: PEM trust anchor bundle used to validate the peer chain
            (RFC 5280 §6). Required unless the system trust store is intended,
            in which case pass ``ca_file=None`` and rely on it deliberately.
        cert_file: Optional client certificate (mTLS).
        key_file: Optional client private key (mTLS).
        token: Service bearer token. Required.

    Returns:
        A connected ``grpc.aio.Channel``.

    Raises:
        TransportConfigurationError: On a missing host/port, a missing or
            empty credential file, or a missing token.
    """
    if not host or not str(host).strip():
        raise TransportConfigurationError("NET binding requires a peer host")
    if not isinstance(port, int) or not (0 < port < 65536):
        raise TransportConfigurationError(
            f"NET binding requires a valid peer port, got {port!r}"
        )

    # Validates presence and non-emptiness; the value is attached below.
    require_service_token(token)

    if (cert_file is None) != (key_file is None):
        raise TransportConfigurationError(
            "mTLS requires both cert_file and key_file; got one without the other"
        )

    root: bytes | None = None
    if ca_file:
        root = _read_required_file(ca_file, "CA bundle")
    private_key = _read_required_file(key_file, "client key") if key_file else None
    certificate_chain = (
        _read_required_file(cert_file, "client certificate") if cert_file else None
    )

    target = f"{str(host).strip()}:{port}"
    authority = (server_name or host).strip()

    credentials = grpc.ssl_channel_credentials(
        root_certificates=root,
        private_key=private_key,
        certificate_chain=certificate_chain,
    )

    options = [
        ("grpc.keepalive_time_ms", KEEPALIVE_TIME_S * 1000),
        ("grpc.keepalive_timeout_ms", KEEPALIVE_TIMEOUT_S * 1000),
        (
            "grpc.keepalive_permit_without_calls",
            1 if KEEPALIVE_PERMIT_WITHOUT_CALLS else 0,
        ),
        ("grpc.max_concurrent_streams", MAX_CONCURRENT_STREAMS),
        # Pin the name checked against the peer certificate, so the authority
        # is the expected identity rather than whatever the dial string holds.
        ("grpc.ssl_target_name_override", authority),
    ]

    logger.debug("brain transport: TLS channel to %s (authority=%s)", target, authority)

    return grpc.aio.secure_channel(target, credentials, options=options)


def bearer_metadata(token: str) -> tuple[tuple[str, str], ...]:
    """Build the per-call metadata that carries the service credential.

    gRPC attaches metadata at call time (``stub.Method(request, metadata=...)``);
    there is no channel-wide metadata argument. Keeping the token out of the
    channel also means it is not held in connection state beyond the call.

    Args:
        token: The service bearer token. Must be non-empty.

    Returns:
        A one-entry metadata tuple for ``authorization``.

    Raises:
        TransportConfigurationError: If the token is blank.
    """
    value = require_service_token(token)
    return (("authorization", f"Bearer {value}"),)


def build_client(
    *,
    host: str,
    port: int,
    token: str,
    server_name: str | None = None,
    ca_file: str | None = None,
    cert_file: str | None = None,
    key_file: str | None = None,
    deadline_s: float | None = None,
) -> BrainClient:
    """Build a working :class:`BrainClient` bound to a remote brain over TLS.

    Args:
        host: Peer hostname or IP.
        port: Peer port.
        token: Service bearer token. Required — this binding is off-host.
        server_name: Expected certificate name; defaults to ``host``.
        ca_file: PEM trust anchor bundle for peer validation.
        cert_file: Client certificate for mTLS.
        key_file: Client key for mTLS.
        deadline_s: Per-call deadline override.

    Returns:
        A ready :class:`BrainClient`.

    Raises:
        TransportConfigurationError: If any required credential is absent.
    """
    # Validates presence and non-emptiness before anything is dialled.
    metadata = bearer_metadata(token)
    channel = build_channel(
        host=host,
        port=port,
        server_name=server_name,
        ca_file=ca_file,
        cert_file=cert_file,
        key_file=key_file,
        token=token,
    )
    kwargs = {} if deadline_s is None else {"deadline_s": deadline_s}
    return BrainClient(channel, metadata=metadata, **kwargs)
