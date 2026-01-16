"""Service endpoint registry for SomaBrain."""

from dataclasses import dataclass
from typing import Optional
import os


@dataclass(frozen=True)
class ServiceEndpoint:
    """Service endpoint configuration."""

    name: str
    env_var: str
    description: str
    default_port: int
    path: str = ""
    required: bool = True
    health_check: Optional[str] = None

    def get_url(
        self, environment: str = "development", host: Optional[str] = None
    ) -> str:
        """Resolve service URL from environment or defaults."""
        url = os.environ.get(self.env_var)
        if url:
            return url.rstrip("/") + self.path

        if environment == "production" and self.required:
            raise ValueError(
                f"Missing required service: {self.env_var}\n"
                f"Service: {self.name} - {self.description}"
            )

        if not host:
            host = self.name.lower().replace(" ", "").replace("-", "")
        if environment == "development":
            host = "localhost"

        return f"http://{host}:{self.default_port}{self.path}"


class ServiceRegistry:
    """SomaBrain service dependencies."""

    SOMAFRACTALMEMORY = ServiceEndpoint(
        name="somafractalmemory",
        env_var="SOMABRAIN_MEMORY_HTTP_ENDPOINT",
        description="Memory system",
        default_port=10101,
        required=True,
        health_check="/health",
    )

    POSTGRES = ServiceEndpoint(
        name="postgres",
        env_var="SOMABRAIN_POSTGRES_DSN",
        description="Database",
        default_port=5432,
        required=True,
    )

    REDIS = ServiceEndpoint(
        name="redis",
        env_var="SOMABRAIN_REDIS_URL",
        description="Cache",
        default_port=6379,
        required=True,
    )

    KAFKA = ServiceEndpoint(
        name="kafka",
        env_var="SOMABRAIN_KAFKA_URL",
        description="Event streaming",
        default_port=9092,
        required=True,
    )

    OPA = ServiceEndpoint(
        name="opa",
        env_var="SOMABRAIN_OPA_URL",
        description="Policy engine",
        default_port=8181,
        required=True,
        health_check="/health",
    )

    KEYCLOAK = ServiceEndpoint(
        name="keycloak",
        env_var="KEYCLOAK_URL",
        description="Identity provider",
        default_port=8080,
        required=False,
        health_check="/health",
    )

    LAGO = ServiceEndpoint(
        name="lago",
        env_var="LAGO_URL",
        description="Billing system",
        default_port=3000,
        required=False,
        health_check="/health",
    )

    @classmethod
    def get_all_services(cls) -> dict[str, ServiceEndpoint]:
        """Return all registered services."""
        return {
            name: getattr(cls, name)
            for name in dir(cls)
            if isinstance(getattr(cls, name), ServiceEndpoint)
        }

    @classmethod
    def validate_required(cls, environment: str) -> list[str]:
        """Return list of missing required service environment variables."""
        missing = []
        for name, service in cls.get_all_services().items():
            if service.required:
                try:
                    service.get_url(environment=environment)
                except ValueError:
                    missing.append(service.env_var)
        return missing


SERVICES = ServiceRegistry()

__all__ = ["ServiceEndpoint", "ServiceRegistry", "SERVICES"]
