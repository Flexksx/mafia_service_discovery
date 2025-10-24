# Service Discovery Package
# Main exports for easy importing

from service_discovery.service_registration.registry import service_registry
from service_discovery.service_registration.health_monitor import health_monitor
from service_discovery.service_registration.health_utils import HealthChecker
from service_discovery.service_registration.health_endpoints import (
    create_health_check_endpoint,
    setup_service_health_checks,
)
from service_discovery.types import (
    ServiceInstance,
    ServiceStatus,
    ServiceRegistrationRequest,
    ServiceRegistrationResponse,
    ServiceHeartbeatRequest,
    ServiceHeartbeatResponse,
    ServiceInstanceResponse,
    ServiceListResponse,
    HealthCheckResult,
)
from service_discovery.client import (
    ServiceDiscoveryClient,
    register_service_with_discovery,
)
from service_discovery.api import api_router

__all__ = [
    # Core registry and monitoring
    "service_registry",
    "health_monitor",
    # Health checking utilities
    "HealthChecker",
    "create_health_check_endpoint",
    "setup_service_health_checks",
    # Types and models
    "ServiceInstance",
    "ServiceStatus",
    "ServiceRegistrationRequest",
    "ServiceRegistrationResponse",
    "ServiceHeartbeatRequest",
    "ServiceHeartbeatResponse",
    "ServiceInstanceResponse",
    "ServiceListResponse",
    "HealthCheckResult",
    # Client
    "ServiceDiscoveryClient",
    "register_service_with_discovery",
    # API
    "api_router",
]
