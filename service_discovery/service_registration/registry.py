from datetime import datetime
from typing import Dict, List, Optional
import asyncio

from service_discovery.types import ServiceInstance, ServiceStatus
from service_discovery.constants import (
    LOG_SERVICE_REGISTERED,
    LOG_SERVICE_UNREGISTERED,
    LOG_EXPIRED_SERVICE_REMOVED,
)
from service_discovery.logger_config import (
    ServiceDiscoveryLogger,
    log_service_registration,
    log_service_unregistration,
)

logger = ServiceDiscoveryLogger.get_logger(__name__)


class ServiceRegistry:
    """Core service registry for tracking service instances"""

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
            log_service_registration(
                logger,
                service_name,
                instance_id,
                service_instance.host,
                service_instance.port,
            )
            return True

    async def unregister_service(self, service_name: str, instance_id: str) -> bool:
        """Unregister a service instance"""
        async with self._lock:
            if self._service_exists(service_name, instance_id):
                del self._services[service_name][instance_id]
                self._cleanup_empty_service(service_name)
                log_service_unregistration(logger, service_name, instance_id)
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
            if self._service_exists(service_name, instance_id):
                service = self._services[service_name][instance_id]
                service.status = status
                service.last_health_check = datetime.now()
                service.load_percentage = load_percentage
                return True
            return False

    async def update_heartbeat(self, service_name: str, instance_id: str) -> bool:
        """Update service heartbeat timestamp"""
        async with self._lock:
            if self._service_exists(service_name, instance_id):
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
                removed_count += await self._cleanup_service_instances(
                    service_name, now, ttl_seconds
                )
                self._cleanup_empty_service(service_name)

            return removed_count

    def _service_exists(self, service_name: str, instance_id: str) -> bool:
        """Check if service instance exists"""
        return (
            service_name in self._services
            and instance_id in self._services[service_name]
        )

    def _cleanup_empty_service(self, service_name: str) -> None:
        """Remove empty service entries"""
        if service_name in self._services and not self._services[service_name]:
            del self._services[service_name]

    async def _cleanup_service_instances(
        self, service_name: str, now: datetime, ttl_seconds: int
    ) -> int:
        """Clean up expired instances for a specific service"""
        removed_count = 0
        for instance_id in list(self._services[service_name].keys()):
            service = self._services[service_name][instance_id]
            if service.last_heartbeat:
                time_since_heartbeat = (now - service.last_heartbeat).total_seconds()
                if time_since_heartbeat > ttl_seconds:
                    del self._services[service_name][instance_id]
                    removed_count += 1
                    logger.warning(
                        LOG_EXPIRED_SERVICE_REMOVED.format(service_name, instance_id)
                    )
        return removed_count

    async def get_all_topic_subscriptions(self) -> Dict[str, List[str]]:
        """Get all topic subscriptions with their subscribed services"""
        async with self._lock:
            topic_map: Dict[str, List[str]] = {}
            
            for service_name, instances in self._services.items():
                for instance in instances.values():
                    for topic in instance.topics:
                        if topic not in topic_map:
                            topic_map[topic] = []
                        if service_name not in topic_map[topic]:
                            topic_map[topic].append(service_name)
            
            return topic_map

    async def get_services_by_topic(self, topic: str) -> List[str]:
        """Get all service names subscribed to a specific topic"""
        async with self._lock:
            service_names = set()
            
            for service_name, instances in self._services.items():
                for instance in instances.values():
                    if topic in instance.topics:
                        service_names.add(service_name)
                        break
            
            return list(service_names)


# Global service registry instance
service_registry = ServiceRegistry()

