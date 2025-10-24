import asyncio
import httpx
import logging
from datetime import datetime
from typing import Dict, List, Optional

from service_discovery.service_registration.registry import service_registry
from service_discovery.types import ServiceInstance, ServiceStatus
from service_discovery.constants import (
    LOG_HEALTH_MONITORING_STARTED,
    LOG_HEALTH_MONITORING_STOPPED,
    LOG_CRITICAL_LOAD_ALERT,
    RETRY_DELAY_SECONDS,
)
from service_discovery.config import (
    HEALTH_CHECK_INTERVAL_SECONDS,
    HEALTH_CHECK_TIMEOUT_SECONDS,
    CRITICAL_LOAD_THRESHOLD,
    SERVICE_REGISTRATION_TTL_SECONDS,
)

logger = logging.getLogger(__name__)


class HealthMonitor:
    """Monitors service health and load"""

    def __init__(self):
        self._running = False
        self._monitoring_task: Optional[asyncio.Task] = None

    async def start_monitoring(self):
        """Start the health monitoring loop"""
        if self._running:
            return

        self._running = True
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info(LOG_HEALTH_MONITORING_STARTED)

    async def stop_monitoring(self):
        """Stop the health monitoring loop"""
        if not self._running:
            return

        self._running = False
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        logger.info(LOG_HEALTH_MONITORING_STOPPED)

    async def _monitoring_loop(self):
        """Main monitoring loop"""
        while self._running:
            try:
                await self._check_all_services()
                await self._cleanup_expired_services()
                await asyncio.sleep(HEALTH_CHECK_INTERVAL_SECONDS)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(RETRY_DELAY_SECONDS)

    async def _check_all_services(self):
        """Check health of all registered services"""
        all_services = await service_registry.get_all_services()
        for service_name, instances in all_services.items():
            for instance in instances:
                await self._check_service_health(instance)

    async def _check_service_health(self, instance: ServiceInstance):
        """Check health of a single service instance"""
        try:
            health_url = (
                f"http://{instance.host}:{instance.port}{instance.health_endpoint}"
            )
            async with httpx.AsyncClient(
                timeout=HEALTH_CHECK_TIMEOUT_SECONDS
            ) as client:
                response = await client.get(health_url)
                await self._process_health_response(instance, response)
        except httpx.TimeoutException:
            await self._handle_health_check_timeout(instance)
        except Exception as e:
            await self._handle_health_check_error(instance, e)

    async def _process_health_response(
        self, instance: ServiceInstance, response: httpx.Response
    ):
        """Process successful health check response"""
        if response.status_code == 200:
            health_data = response.json()
            load_percentage = health_data.get("load_percentage", 0.0)

            await service_registry.update_service_health(
                instance.service_name,
                instance.instance_id,
                ServiceStatus.HEALTHY,
                load_percentage,
            )

            if load_percentage >= CRITICAL_LOAD_THRESHOLD:
                logger.warning(
                    LOG_CRITICAL_LOAD_ALERT.format(
                        instance.service_name,
                        instance.instance_id,
                        load_percentage,
                        CRITICAL_LOAD_THRESHOLD,
                    )
                )
        else:
            await service_registry.update_service_health(
                instance.service_name, instance.instance_id, ServiceStatus.UNHEALTHY
            )
            logger.warning(
                f"Health check failed for {instance.service_name}:{instance.instance_id} - Status: {response.status_code}"
            )

    async def _handle_health_check_timeout(self, instance: ServiceInstance):
        """Handle health check timeout"""
        await service_registry.update_service_health(
            instance.service_name, instance.instance_id, ServiceStatus.UNHEALTHY
        )
        logger.warning(
            f"Health check timeout for {instance.service_name}:{instance.instance_id}"
        )

    async def _handle_health_check_error(
        self, instance: ServiceInstance, error: Exception
    ):
        """Handle health check error"""
        await service_registry.update_service_health(
            instance.service_name, instance.instance_id, ServiceStatus.UNHEALTHY
        )
        logger.error(
            f"Health check error for {instance.service_name}:{instance.instance_id}: {error}"
        )

    async def _cleanup_expired_services(self):
        """Remove services that haven't sent heartbeat within TTL"""
        removed_count = await service_registry.cleanup_expired_services(
            SERVICE_REGISTRATION_TTL_SECONDS
        )
        if removed_count > 0:
            logger.info(f"Cleaned up {removed_count} expired services")


# Global health monitor instance
health_monitor = HealthMonitor()
