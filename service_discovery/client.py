import asyncio
import httpx
import logging
from typing import Dict, Optional, List
import os

from service_discovery.types import ServiceInstance, ServiceRegistrationRequest
from service_discovery.constants import (
    BEARER_PREFIX,
    DEFAULT_HEARTBEAT_INTERVAL,
    HEARTBEAT_RETRY_DELAY,
    LOG_HEARTBEAT_LOOP_STARTED,
    LOG_HEARTBEAT_LOOP_STOPPED,
)

logger = logging.getLogger(__name__)


class ServiceDiscoveryClient:
    """Client library for interacting with the service discovery service"""

    def __init__(
        self, service_discovery_url: str = None, service_discovery_secret: str = None
    ):
        self.service_discovery_url = service_discovery_url or os.getenv(
            "SERVICE_DISCOVERY_URL", "http://service-discovery:3004"
        )
        self.service_discovery_secret = service_discovery_secret or os.getenv(
            "SERVICE_DISCOVERY_SECRET", "service-discovery-secret-change-me"
        )
        self._headers = {
            "Authorization": f"{BEARER_PREFIX}{self.service_discovery_secret}",
            "Content-Type": "application/json",
        }
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._registered_service: Optional[Dict] = None

    async def register_service(
        self,
        service_name: str,
        instance_id: str,
        host: str,
        port: int,
        health_endpoint: str = "/health",
        metadata: Dict[str, str] = None,
    ) -> bool:
        """Register this service instance with the service discovery"""
        try:
            registration_data = ServiceRegistrationRequest(
                service_name=service_name,
                instance_id=instance_id,
                host=host,
                port=port,
                health_endpoint=health_endpoint,
                metadata=metadata or {},
            )

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.service_discovery_url}/v1/discovery/register",
                    json=registration_data.dict(),
                    headers=self._headers,
                )

                if response.status_code == 200:
                    result = response.json()
                    if result.get("success"):
                        self._registered_service = registration_data.dict()
                        logger.info(
                            f"Successfully registered service: {service_name}:{instance_id}"
                        )
                        return True
                    else:
                        logger.error(f"Registration failed: {result.get('message')}")
                        return False
                else:
                    logger.error(
                        f"Registration failed with status {response.status_code}: {response.text}"
                    )
                    return False

        except Exception as e:
            logger.error(f"Error registering service: {e}")
            return False

    async def send_heartbeat(self) -> bool:
        """Send heartbeat to maintain service registration"""
        if not self._registered_service:
            logger.warning("No registered service to send heartbeat for")
            return False

        try:
            heartbeat_data = {
                "service_name": self._registered_service["service_name"],
                "instance_id": self._registered_service["instance_id"],
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.service_discovery_url}/v1/discovery/heartbeat",
                    json=heartbeat_data,
                    headers=self._headers,
                )

                if response.status_code == 200:
                    result = response.json()
                    if result.get("success"):
                        logger.debug(
                            f"Heartbeat sent for {self._registered_service['service_name']}:{self._registered_service['instance_id']}"
                        )
                        return True
                    else:
                        logger.warning(f"Heartbeat failed: {result.get('message')}")
                        return False
                else:
                    logger.warning(
                        f"Heartbeat failed with status {response.status_code}"
                    )
                    return False

        except Exception as e:
            logger.error(f"Error sending heartbeat: {e}")
            return False

    async def start_heartbeat_loop(
        self, interval_seconds: int = DEFAULT_HEARTBEAT_INTERVAL
    ):
        """Start periodic heartbeat sending"""
        if self._heartbeat_task and not self._heartbeat_task.done():
            logger.warning("Heartbeat loop already running")
            return

        self._heartbeat_task = asyncio.create_task(
            self._heartbeat_loop(interval_seconds)
        )
        logger.info(LOG_HEARTBEAT_LOOP_STARTED.format(interval_seconds))

    async def stop_heartbeat_loop(self):
        """Stop the heartbeat loop"""
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
            logger.info(LOG_HEARTBEAT_LOOP_STOPPED)

    async def _heartbeat_loop(self, interval_seconds: int):
        """Internal heartbeat loop"""
        while True:
            try:
                await self.send_heartbeat()
                await asyncio.sleep(interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")
                await asyncio.sleep(HEARTBEAT_RETRY_DELAY)

    async def unregister_service(self) -> bool:
        """Unregister this service instance"""
        if not self._registered_service:
            logger.warning("No registered service to unregister")
            return False

        try:
            service_name = self._registered_service["service_name"]
            instance_id = self._registered_service["instance_id"]

            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    f"{self.service_discovery_url}/v1/discovery/unregister/{service_name}/{instance_id}",
                    headers=self._headers,
                )

                if response.status_code == 200:
                    logger.info(
                        f"Successfully unregistered service: {service_name}:{instance_id}"
                    )
                    self._registered_service = None
                    return True
                else:
                    logger.error(
                        f"Unregistration failed with status {response.status_code}"
                    )
                    return False

        except Exception as e:
            logger.error(f"Error unregistering service: {e}")
            return False

    async def discover_services(
        self, service_name: str, healthy_only: bool = True
    ) -> List[ServiceInstance]:
        """Discover instances of a specific service"""
        try:
            endpoint = f"/services/{service_name}"
            if healthy_only:
                endpoint += "/healthy"

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.service_discovery_url}/v1/discovery{endpoint}"
                )

                if response.status_code == 200:
                    data = response.json()
                    instances = []

                    if healthy_only:
                        service_instances = data.get("healthy_instances", [])
                    else:
                        service_instances = data.get("instances", [])

                    for instance_data in service_instances:
                        instance = ServiceInstance(
                            service_name=instance_data["service_name"],
                            instance_id=instance_data["instance_id"],
                            host=instance_data["host"],
                            port=instance_data["port"],
                            health_endpoint=instance_data["health_endpoint"],
                            status=instance_data["status"],
                            load_percentage=instance_data["load_percentage"],
                            metadata=instance_data["metadata"],
                        )
                        instances.append(instance)

                    return instances
                else:
                    logger.error(
                        f"Service discovery failed with status {response.status_code}"
                    )
                    return []

        except Exception as e:
            logger.error(f"Error discovering services: {e}")
            return []

    async def list_all_services(self) -> Dict[str, List[ServiceInstance]]:
        """List all registered services"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.service_discovery_url}/v1/discovery/services"
                )

                if response.status_code == 200:
                    data = response.json()
                    services = {}

                    for service_name, instances_data in data.get(
                        "services", {}
                    ).items():
                        instances = []
                        for instance_data in instances_data:
                            instance = ServiceInstance(
                                service_name=instance_data["service_name"],
                                instance_id=instance_data["instance_id"],
                                host=instance_data["host"],
                                port=instance_data["port"],
                                health_endpoint=instance_data["health_endpoint"],
                                status=instance_data["status"],
                                load_percentage=instance_data["load_percentage"],
                                metadata=instance_data["metadata"],
                            )
                            instances.append(instance)
                        services[service_name] = instances

                    return services
                else:
                    logger.error(
                        f"Service listing failed with status {response.status_code}"
                    )
                    return {}

        except Exception as e:
            logger.error(f"Error listing services: {e}")
            return {}


async def register_service_with_discovery(
    service_name: str,
    instance_id: str,
    host: str,
    port: int,
    health_endpoint: str = "/health",
    metadata: Dict[str, str] = None,
    heartbeat_interval: int = DEFAULT_HEARTBEAT_INTERVAL,
) -> ServiceDiscoveryClient:
    """Convenience function to register a service and start heartbeat loop"""
    client = ServiceDiscoveryClient()

    success = await client.register_service(
        service_name=service_name,
        instance_id=instance_id,
        host=host,
        port=port,
        health_endpoint=health_endpoint,
        metadata=metadata,
    )

    if success:
        await client.start_heartbeat_loop(heartbeat_interval)
        return client
    else:
        raise Exception("Failed to register service with discovery")
