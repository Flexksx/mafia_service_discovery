from datetime import datetime
from typing import Dict, Optional, List
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import logging

logger = logging.getLogger(__name__)


class ServiceStatus(Enum):
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class ServiceInstance:
    service_name: str
    instance_id: str
    host: str
    port: int
    health_endpoint: str
    status: ServiceStatus = ServiceStatus.UNKNOWN
    last_health_check: Optional[datetime] = None
    last_heartbeat: Optional[datetime] = None
    load_percentage: float = 0.0
    metadata: Dict[str, str] = field(default_factory=dict)
    registered_at: datetime = field(default_factory=datetime.now)


class ServiceRegistry:
    """In-memory service registry for tracking service instances"""

    def __init__(self):
        self._services: Dict[str, Dict[str, ServiceInstance]] = {}
        self._lock = asyncio.Lock()

    async def register_service(self, service_instance: ServiceInstance) -> bool:
        """Register a new service instance"""
        async with self._lock:
            service_name = service_instance.service_name
            instance_id = service_instance.instance_id

            if service_name not in self._services:
                self._services[service_name] = {}

            self._services[service_name][instance_id] = service_instance
            logger.info(
                f"Registered service: {service_name}:{instance_id} at {service_instance.host}:{service_instance.port}"
            )
            return True

    async def unregister_service(self, service_name: str, instance_id: str) -> bool:
        """Unregister a service instance"""
        async with self._lock:
            if (
                service_name in self._services
                and instance_id in self._services[service_name]
            ):
                del self._services[service_name][instance_id]
                if not self._services[service_name]:
                    del self._services[service_name]
                logger.info(f"Unregistered service: {service_name}:{instance_id}")
                return True
            return False

    async def update_service_health(
        self,
        service_name: str,
        instance_id: str,
        status: ServiceStatus,
        load_percentage: float = 0.0,
    ) -> bool:
        """Update service health status"""
        async with self._lock:
            if (
                service_name in self._services
                and instance_id in self._services[service_name]
            ):
                service = self._services[service_name][instance_id]
                service.status = status
                service.last_health_check = datetime.now()
                service.load_percentage = load_percentage
                return True
            return False

    async def update_heartbeat(self, service_name: str, instance_id: str) -> bool:
        """Update service heartbeat timestamp"""
        async with self._lock:
            if (
                service_name in self._services
                and instance_id in self._services[service_name]
            ):
                service = self._services[service_name][instance_id]
                service.last_heartbeat = datetime.now()
                return True
            return False

    async def get_service_instances(self, service_name: str) -> List[ServiceInstance]:
        """Get all instances of a service"""
        async with self._lock:
            if service_name in self._services:
                return list(self._services[service_name].values())
            return []

    async def get_healthy_service_instances(
        self, service_name: str
    ) -> List[ServiceInstance]:
        """Get only healthy instances of a service"""
        instances = await self.get_service_instances(service_name)
        return [
            instance
            for instance in instances
            if instance.status == ServiceStatus.HEALTHY
        ]

    async def get_all_services(self) -> Dict[str, List[ServiceInstance]]:
        """Get all registered services"""
        async with self._lock:
            return {
                name: list(instances.values())
                for name, instances in self._services.items()
            }

    async def cleanup_expired_services(self, ttl_seconds: int) -> int:
        """Remove services that haven't sent heartbeat within TTL"""
        async with self._lock:
            now = datetime.now()
            removed_count = 0

            for service_name in list(self._services.keys()):
                for instance_id in list(self._services[service_name].keys()):
                    service = self._services[service_name][instance_id]
                    if service.last_heartbeat:
                        time_since_heartbeat = (
                            now - service.last_heartbeat
                        ).total_seconds()
                        if time_since_heartbeat > ttl_seconds:
                            del self._services[service_name][instance_id]
                            removed_count += 1
                            logger.warning(
                                f"Removed expired service: {service_name}:{instance_id}"
                            )

                # Remove empty service entries
                if not self._services[service_name]:
                    del self._services[service_name]

            return removed_count


# Global service registry instance
service_registry = ServiceRegistry()
