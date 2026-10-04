"""Start the production gRPC Brain service.

LOCAL binds ``/run/soma/brain.sock`` mode 0600 (filesystem ACL, no bearer).
NET binds TCP + TLS 1.3 using the configured server certificate and key.

Both bindings register the same ``MemoryService`` the HTTP routes use — one
write path, one read path (PLAN §1).
"""

from __future__ import annotations

import asyncio
import logging

from django.core.management.base import BaseCommand, CommandError

logger = logging.getLogger("somabrain.management.serve_brain_grpc")


class Command(BaseCommand):
    help = "Serve soma.brain.v1.Brain over LOCAL (UDS) or NET (TCP+TLS)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--mode",
            dest="mode",
            default=None,
            help="LOCAL or NET (defaults to SA01_DEPLOYMENT_MODE / settings)",
        )
        parser.add_argument(
            "--socket",
            dest="socket",
            default=None,
            help="Override the LOCAL Unix socket path",
        )

    def handle(self, *args, **options):
        mode = options.get("mode") or self._configured_mode()
        try:
            asyncio.run(self._serve(mode, options.get("socket")))
        except KeyboardInterrupt:
            self.stdout.write("brain gRPC server stopped")

    def _configured_mode(self) -> str:
        from django.conf import settings

        return (
            getattr(settings, "SA01_DEPLOYMENT_MODE", None)
            or getattr(settings, "SOMA_DEPLOY_MODE", None)
            or ""
        )

    async def _serve(self, mode: str, socket_path: str | None) -> None:
        import grpc

        from somabrain.api.memory.helpers import _get_memory_pool, _resolve_namespace
        from somabrain.services.memory_service import MemoryService
        from somabrain.transport.port import TransportBinding, resolve_binding
        from somabrain.transport.serve import add_brain_service

        binding = resolve_binding(mode)

        pool = _get_memory_pool()
        if pool is None:
            raise CommandError("memory pool unavailable; cannot serve Brain")

        def service_for_namespace(namespace: str):
            return MemoryService(pool, namespace)

        server = grpc.aio.server()
        await add_brain_service(
            server,
            service_for_namespace=service_for_namespace,
            resolve_namespace=_resolve_namespace,
        )

        if binding is TransportBinding.LOCAL:
            from somabrain.transport.uds import start_local_server

            path = socket_path or self._local_socket_path()
            target = await start_local_server(server, path=path)
            self.stdout.write(self.style.SUCCESS(f"Brain gRPC (LOCAL) on {target}"))
        else:
            target = await self._start_net(server)
            self.stdout.write(self.style.SUCCESS(f"Brain gRPC (NET) on {target}"))

        await server.wait_for_termination()

    def _local_socket_path(self) -> str:
        from django.conf import settings

        return (
            getattr(settings, "SOMABRAIN_GRPC_SOCKET", None)
            or __import__(
                "somabrain.transport.port", fromlist=["BRAIN_SOCK"]
            ).BRAIN_SOCK
        )

    async def _start_net(self, server) -> str:
        from django.conf import settings

        from somabrain.transport.net import _read_required_file

        cert_file = getattr(settings, "SOMABRAIN_GRPC_CERT_FILE", "") or ""
        key_file = getattr(settings, "SOMABRAIN_GRPC_KEY_FILE", "") or ""
        if not cert_file or not key_file:
            raise CommandError(
                "NET binding requires SOMABRAIN_GRPC_CERT_FILE and "
                "SOMABRAIN_GRPC_KEY_FILE; refusing to serve plaintext"
            )
        cert = _read_required_file(cert_file, "gRPC server certificate")
        key = _read_required_file(key_file, "gRPC server key")

        host = getattr(settings, "SOMABRAIN_GRPC_LISTEN_HOST", "0.0.0.0")
        port = int(getattr(settings, "SOMABRAIN_GRPC_LISTEN_PORT", 30102))
        creds = grpc.ssl_server_credentials(
            [(key, cert)],
            root_certificates=None,
            require_client_auth=False,
        )
        bound = server.add_secure_port(f"{host}:{port}", creds)
        if not bound:
            raise CommandError(f"gRPC failed to bind {host}:{port}")
        await server.start()
        return f"{host}:{port} (TLS)"
