import asyncio
import httpx
import logging
from datetime import datetime
from typing import Dict, List
from service_discovery.registry import service_registry, ServiceStatus, ServiceInstance
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
        self._monitoring_task: asyncio.Task = None

    async def start_monitoring(self):
        """Start the health monitoring loop"""
        if self._running:
            return

        self._running = True
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info("Health monitoring started")

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
        logger.info("Health monitoring stopped")

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
                await asyncio.sleep(5)  # Short delay before retrying

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

                if response.status_code == 200:
                    health_data = response.json()
                    load_percentage = health_data.get("load_percentage", 0.0)

                    # Update service status
                    await service_registry.update_service_health(
                        instance.service_name,
                        instance.instance_id,
                        ServiceStatus.HEALTHY,
                        load_percentage,
                    )

                    # Check for critical load
                    if load_percentage >= CRITICAL_LOAD_THRESHOLD:
                        logger.warning(
                            f"CRITICAL LOAD ALERT: Service {instance.service_name}:{instance.instance_id} "
                            f"is at {load_percentage:.1%} load (threshold: {CRITICAL_LOAD_THRESHOLD:.1%})"
                        )

                    logger.debug(
                        f"Health check passed for {instance.service_name}:{instance.instance_id}"
                    )
                else:
                    await service_registry.update_service_health(
                        instance.service_name,
                        instance.instance_id,
                        ServiceStatus.UNHEALTHY,
                    )
                    logger.warning(
                        f"Health check failed for {instance.service_name}:{instance.instance_id} - Status: {response.status_code}"
                    )

        except httpx.TimeoutException:
            await service_registry.update_service_health(
                instance.service_name, instance.instance_id, ServiceStatus.UNHEALTHY
            )
            logger.warning(
                f"Health check timeout for {instance.service_name}:{instance.instance_id}"
            )

        except Exception as e:
            await service_registry.update_service_health(
                instance.service_name, instance.instance_id, ServiceStatus.UNHEALTHY
            )
            logger.error(
                f"Health check error for {instance.service_name}:{instance.instance_id}: {e}"
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
