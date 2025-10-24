import asyncio
import httpx
import logging
import time
import os
import random
import socket
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


def get_next_port() -> int:
    """Get a random available port"""
    while True:
        port = random.randint(9000, 9999)  # Use higher port range to avoid conflicts
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("localhost", port))
                return port
        except OSError:
            continue  # Port is in use, try another one


def reset_port_counter():
    """No-op for random port assignment"""
    pass


@dataclass
class ServiceInstanceData:
    service_name: str
    instance_id: str
    host: str
    port: int
    health_endpoint: str = "/health"
    metadata: Dict[str, str] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class ServiceDiscoveryTestClient:
    """Test client for interacting with the service discovery service"""

    def __init__(
        self, base_url: str = "http://localhost:3004", secret: str = "test-secret-key"
    ):
        self.base_url = base_url
        self.secret = secret
        self.headers = {
            "Authorization": f"Bearer {self.secret}",
            "Content-Type": "application/json",
        }

    async def health_check(self) -> bool:
        """Check if the service discovery service is healthy"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/health")
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

    async def wait_for_service(self, timeout: int = 60) -> bool:
        """Wait for the service discovery service to be ready"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            if await self.health_check():
                logger.info("Service discovery service is ready")
                return True
            logger.info("Waiting for service discovery service...")
            await asyncio.sleep(2)

        logger.error(f"Service discovery service not ready after {timeout} seconds")
        return False

    async def register_service(self, service: ServiceInstanceData) -> bool:
        """Register a service instance"""
        try:
            registration_data = {
                "service_name": service.service_name,
                "instance_id": service.instance_id,
                "host": service.host,
                "port": service.port,
                "health_endpoint": service.health_endpoint,
                "metadata": service.metadata,
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/v1/discovery/register",
                    json=registration_data,
                    headers=self.headers,
                )

                if response.status_code == 200:
                    result = response.json()
                    success = result.get("success", False)
                    logger.info(
                        f"Service registration {'succeeded' if success else 'failed'}: {result.get('message', '')}"
                    )
                    return success
                else:
                    logger.error(
                        f"Registration failed with status {response.status_code}: {response.text}"
                    )
                    return False

        except Exception as e:
            logger.error(f"Error registering service: {e}")
            return False

    async def send_heartbeat(self, service_name: str, instance_id: str) -> bool:
        """Send heartbeat for a service instance"""
        try:
            heartbeat_data = {
                "service_name": service_name,
                "instance_id": instance_id,
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/v1/discovery/heartbeat",
                    json=heartbeat_data,
                    headers=self.headers,
                )

                if response.status_code == 200:
                    result = response.json()
                    success = result.get("success", False)
                    logger.info(
                        f"Heartbeat {'succeeded' if success else 'failed'}: {result.get('message', '')}"
                    )
                    return success
                else:
                    logger.error(
                        f"Heartbeat failed with status {response.status_code}: {response.text}"
                    )
                    return False

        except Exception as e:
            logger.error(f"Error sending heartbeat: {e}")
            return False

    async def unregister_service(self, service_name: str, instance_id: str) -> bool:
        """Unregister a service instance"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    f"{self.base_url}/v1/discovery/unregister/{service_name}/{instance_id}",
                    headers=self.headers,
                )

                if response.status_code == 200:
                    result = response.json()
                    success = result.get("success", False)
                    logger.info(
                        f"Service unregistration {'succeeded' if success else 'failed'}: {result.get('message', '')}"
                    )
                    return success
                else:
                    logger.error(
                        f"Unregistration failed with status {response.status_code}: {response.text}"
                    )
                    return False

        except Exception as e:
            logger.error(f"Error unregistering service: {e}")
            return False

    async def get_service_instances(self, service_name: str) -> List[Dict]:
        """Get all instances of a service"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/v1/discovery/services/{service_name}"
                )

                if response.status_code == 200:
                    data = response.json()
                    return data.get("instances", [])
                else:
                    logger.error(
                        f"Failed to get service instances: {response.status_code}"
                    )
                    return []

        except Exception as e:
            logger.error(f"Error getting service instances: {e}")
            return []

    async def get_healthy_service_instances(self, service_name: str) -> List[Dict]:
        """Get healthy instances of a service"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/v1/discovery/services/{service_name}/healthy"
                )

                if response.status_code == 200:
                    data = response.json()
                    return data.get("healthy_instances", [])
                else:
                    logger.error(
                        f"Failed to get healthy service instances: {response.status_code}"
                    )
                    return []

        except Exception as e:
            logger.error(f"Error getting healthy service instances: {e}")
            return []

    async def list_all_services(self) -> Dict[str, List[Dict]]:
        """List all registered services"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/v1/discovery/services")

                if response.status_code == 200:
                    data = response.json()
                    return data.get("services", {})
                else:
                    logger.error(f"Failed to list services: {response.status_code}")
                    return {}

        except Exception as e:
            logger.error(f"Error listing services: {e}")
            return {}

    async def get_prometheus_targets(self, service_name: str) -> List[Dict]:
        """Get service instances in Prometheus format"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/v1/discovery/services/{service_name}/instances"
                )

                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(
                        f"Failed to get Prometheus targets: {response.status_code}"
                    )
                    return []

        except Exception as e:
            logger.error(f"Error getting Prometheus targets: {e}")
            return []

    async def get_monitoring_stats(self) -> Dict:
        """Get health monitoring statistics"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/v1/discovery/monitoring/stats"
                )

                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(
                        f"Failed to get monitoring stats: {response.status_code}"
                    )
                    return {}

        except Exception as e:
            logger.error(f"Error getting monitoring stats: {e}")
            return {}

    async def get_monitoring_health(self) -> Dict:
        """Get monitoring system health status"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/v1/discovery/monitoring/health"
                )

                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(
                        f"Failed to get monitoring health: {response.status_code}"
                    )
                    return {}

        except Exception as e:
            logger.error(f"Error getting monitoring health: {e}")
            return {}

    async def reset_monitoring_stats(self) -> bool:
        """Reset monitoring statistics (requires authentication)"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/v1/discovery/monitoring/reset-stats",
                    headers=self.headers,
                )

                if response.status_code == 200:
                    result = response.json()
                    success = result.get("success", False)
                    logger.info(
                        f"Monitoring stats reset {'succeeded' if success else 'failed'}: {result.get('message', '')}"
                    )
                    return success
                else:
                    logger.error(
                        f"Reset monitoring stats failed with status {response.status_code}: {response.text}"
                    )
                    return False

        except Exception as e:
            logger.error(f"Error resetting monitoring stats: {e}")
            return False


class MockService:
    """Mock service that simulates a real service for testing"""

    def __init__(
        self,
        service_name: str,
        instance_id: str,
        port: int = None,
        load_percentage: float = 0.1,
    ):
        self.service_name = service_name
        self.instance_id = instance_id
        self.port = port
        self.host = "localhost"
        self.health_endpoint = "/health"
        self.metadata = {"environment": "test", "version": "1.0.0"}
        self.load_percentage = load_percentage  # Simulated load percentage
        self._running = False
        self._server = None

    async def _ensure_port(self):
        """Ensure we have a port assigned"""
        if self.port is None:
            self.port = get_next_port()

    async def start(self):
        """Start the mock service"""
        await self._ensure_port()

        from fastapi import FastAPI
        import uvicorn

        app = FastAPI(title=f"Mock {self.service_name}")

        @app.get("/health")
        async def health():
            return {
                "status": "healthy",
                "service": self.service_name,
                "instance": self.instance_id,
                "timestamp": datetime.now().isoformat(),
                "load_percentage": self.load_percentage,
            }

        @app.get("/")
        async def root():
            return {"message": f"Mock {self.service_name} is running"}

        # Start the server in a separate task
        config = uvicorn.Config(app, host="0.0.0.0", port=self.port, log_level="error")
        self._server = uvicorn.Server(config)
        self._running = True

        # Run server in background
        asyncio.create_task(self._server.serve())

    async def stop(self):
        """Stop the mock service"""
        if self._server and self._running:
            self._server.should_exit = True
            self._running = False

    def set_load_percentage(self, load_percentage: float):
        """Set the simulated load percentage for this service"""
        self.load_percentage = max(
            0.0, min(1.0, load_percentage)
        )  # Clamp between 0 and 1

    def get_test_instance(self) -> ServiceInstanceData:
        """Get ServiceInstanceData for this mock service"""
        return ServiceInstanceData(
            service_name=self.service_name,
            instance_id=self.instance_id,
            host=self.host,
            port=self.port,
            health_endpoint=self.health_endpoint,
            metadata=self.metadata,
        )
