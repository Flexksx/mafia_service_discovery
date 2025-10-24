import asyncio
import httpx
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from dataclasses import dataclass

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
    WARNING_LOAD_THRESHOLD,
    EMERGENCY_LOAD_THRESHOLD,
    SERVICE_REGISTRATION_TTL_SECONDS,
    MONITORING_ENABLED,
    HEALTH_CHECK_RETRY_ATTEMPTS,
    HEALTH_CHECK_RETRY_DELAY_SECONDS,
    ALERT_COOLDOWN_SECONDS,
    MAX_CONCURRENT_HEALTH_CHECKS,
    EXPECTED_HEALTH_RESPONSE_FIELDS,
    HEALTH_CHECK_SUCCESS_STATUS,
)
from service_discovery.logger_config import (
    ServiceDiscoveryLogger,
    log_health_check_success,
    log_health_check_failure,
    log_critical_load_alert,
)

logger = ServiceDiscoveryLogger.get_logger(__name__)


@dataclass
class AlertState:
    """Track alert state to prevent spam"""

    last_alert_time: Optional[datetime] = None
    alert_count: int = 0
    service_name: str = ""
    instance_id: str = ""


class HealthMonitor:
    """Enhanced service health and load monitor with alerting capabilities"""

    def __init__(self):
        self._running = False
        self._monitoring_task: Optional[asyncio.Task] = None
        self._alert_states: Dict[str, AlertState] = {}  # Track alert states per service
        self._semaphore = asyncio.Semaphore(MAX_CONCURRENT_HEALTH_CHECKS)
        self._monitoring_stats = {
            "total_checks": 0,
            "successful_checks": 0,
            "failed_checks": 0,
            "critical_alerts": 0,
            "warning_alerts": 0,
            "emergency_alerts": 0,
        }

    async def start_monitoring(self):
        """Start the health monitoring loop"""
        if self._running:
            return

        if not MONITORING_ENABLED:
            logger.info("Health monitoring is disabled")
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
            finally:
                self._monitoring_task = None
        logger.info(LOG_HEALTH_MONITORING_STOPPED)

    async def _monitoring_loop(self):
        """Main monitoring loop with enhanced error handling and statistics"""
        while self._running:
            try:
                start_time = time.time()
                await self._check_all_services_concurrent()
                await self._cleanup_expired_services()

                # Log monitoring statistics periodically
                if (
                    self._monitoring_stats["total_checks"] % 100 == 0
                    and self._monitoring_stats["total_checks"] > 0
                ):
                    self._log_monitoring_stats()

                # Calculate sleep time to maintain consistent interval
                elapsed_time = time.time() - start_time
                sleep_time = max(0, HEALTH_CHECK_INTERVAL_SECONDS - elapsed_time)
                await asyncio.sleep(sleep_time)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(
                    f"Error in monitoring loop: {e}",
                    extra={"error_type": "monitoring_loop_error"},
                )
                await asyncio.sleep(RETRY_DELAY_SECONDS)

    async def _check_all_services_concurrent(self):
        """Check health of all registered services concurrently"""
        all_services = await service_registry.get_all_services()

        # Create tasks for all service instances
        tasks = []
        for service_name, instances in all_services.items():
            for instance in instances:
                task = self._check_service_health_with_semaphore(instance)
                tasks.append(task)

        # Execute all health checks concurrently
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _check_service_health_with_semaphore(self, instance: ServiceInstance):
        """Check service health with semaphore to limit concurrent requests"""
        async with self._semaphore:
            await self._check_service_health(instance)

    async def _check_all_services(self):
        """Check health of all registered services (legacy method)"""
        all_services = await service_registry.get_all_services()
        for service_name, instances in all_services.items():
            for instance in instances:
                await self._check_service_health(instance)

    async def _check_service_health(self, instance: ServiceInstance):
        """Check health of a single service instance with retry logic"""
        self._monitoring_stats["total_checks"] += 1

        health_url = f"http://{instance.host}:{instance.port}{instance.health_endpoint}"

        for attempt in range(HEALTH_CHECK_RETRY_ATTEMPTS):
            try:
                start_time = time.time()
                async with httpx.AsyncClient(
                    timeout=HEALTH_CHECK_TIMEOUT_SECONDS
                ) as client:
                    response = await client.get(health_url)
                    response_time_ms = (time.time() - start_time) * 1000

                    await self._process_health_response(
                        instance, response, response_time_ms
                    )
                    self._monitoring_stats["successful_checks"] += 1
                    return

            except httpx.TimeoutException:
                if attempt == HEALTH_CHECK_RETRY_ATTEMPTS - 1:
                    await self._handle_health_check_timeout(instance)
                    self._monitoring_stats["failed_checks"] += 1
                else:
                    await asyncio.sleep(HEALTH_CHECK_RETRY_DELAY_SECONDS)

            except Exception as e:
                if attempt == HEALTH_CHECK_RETRY_ATTEMPTS - 1:
                    await self._handle_health_check_error(instance, e)
                    self._monitoring_stats["failed_checks"] += 1
                else:
                    await asyncio.sleep(HEALTH_CHECK_RETRY_DELAY_SECONDS)

    async def _process_health_response(
        self,
        instance: ServiceInstance,
        response: httpx.Response,
        response_time_ms: float,
    ):
        """Process successful health check response with enhanced load monitoring"""
        if response.status_code == 200:
            try:
                health_data = response.json()

                # Validate response structure
                if not self._validate_health_response(health_data):
                    await self._handle_invalid_health_response(instance, health_data)
                    return

                load_percentage = health_data.get("load_percentage", 0.0)
                service_status = health_data.get("status", HEALTH_CHECK_SUCCESS_STATUS)

                # Update service health
                await service_registry.update_service_health(
                    instance.service_name,
                    instance.instance_id,
                    (
                        ServiceStatus.HEALTHY
                        if service_status == HEALTH_CHECK_SUCCESS_STATUS
                        else ServiceStatus.UNHEALTHY
                    ),
                    load_percentage,
                )

                # Log successful health check
                log_health_check_success(
                    logger,
                    instance.service_name,
                    instance.instance_id,
                    load_percentage,
                    response_time_ms,
                    instance.health_endpoint,
                )

                # Check for load alerts
                await self._check_load_alerts(instance, load_percentage)

            except Exception as e:
                await self._handle_health_check_error(instance, e)
        else:
            await service_registry.update_service_health(
                instance.service_name, instance.instance_id, ServiceStatus.UNHEALTHY
            )
            log_health_check_failure(
                logger,
                instance.service_name,
                instance.instance_id,
                f"HTTP {response.status_code}",
                instance.health_endpoint,
            )

    def _validate_health_response(self, health_data: dict) -> bool:
        """Validate health check response structure"""
        if not isinstance(health_data, dict):
            return False

        # Check for required fields
        for field in EXPECTED_HEALTH_RESPONSE_FIELDS:
            if field not in health_data:
                return False

        # Validate load_percentage is a number between 0 and 1
        load_percentage = health_data.get("load_percentage")
        if not isinstance(load_percentage, (int, float)) or not (
            0 <= load_percentage <= 1
        ):
            return False

        return True

    async def _handle_invalid_health_response(
        self, instance: ServiceInstance, health_data: dict
    ):
        """Handle invalid health check response"""
        await service_registry.update_service_health(
            instance.service_name, instance.instance_id, ServiceStatus.UNHEALTHY
        )
        logger.warning(
            f"Invalid health response from {instance.service_name}:{instance.instance_id}: {health_data}",
            extra={
                "service_name": instance.service_name,
                "instance_id": instance.instance_id,
                "invalid_response": health_data,
                "error_type": "invalid_health_response",
            },
        )

    async def _check_load_alerts(
        self, instance: ServiceInstance, load_percentage: float
    ):
        """Check for load-based alerts with cooldown"""
        service_key = f"{instance.service_name}:{instance.instance_id}"

        # Determine alert level
        alert_level = None
        threshold = None
        if load_percentage >= EMERGENCY_LOAD_THRESHOLD:
            alert_level = "emergency"
            threshold = EMERGENCY_LOAD_THRESHOLD
        elif load_percentage >= CRITICAL_LOAD_THRESHOLD:
            alert_level = "critical"
            threshold = CRITICAL_LOAD_THRESHOLD
        elif load_percentage >= WARNING_LOAD_THRESHOLD:
            alert_level = "warning"
            threshold = WARNING_LOAD_THRESHOLD

        if alert_level and threshold is not None:
            await self._send_load_alert(
                instance, load_percentage, threshold, alert_level, service_key
            )

    async def _send_load_alert(
        self,
        instance: ServiceInstance,
        load_percentage: float,
        threshold: float,
        alert_level: str,
        service_key: str,
    ):
        """Send load alert with cooldown management"""
        now = datetime.now()

        # Get or create alert state
        if service_key not in self._alert_states:
            self._alert_states[service_key] = AlertState(
                service_name=instance.service_name, instance_id=instance.instance_id
            )

        alert_state = self._alert_states[service_key]

        # Check cooldown
        if (
            alert_state.last_alert_time
            and (now - alert_state.last_alert_time).total_seconds()
            < ALERT_COOLDOWN_SECONDS
        ):
            return

        # Update alert state
        alert_state.last_alert_time = now
        alert_state.alert_count += 1

        # Update statistics
        self._monitoring_stats[f"{alert_level}_alerts"] += 1

        # Log alert
        if alert_level == "critical":
            log_critical_load_alert(
                logger,
                instance.service_name,
                instance.instance_id,
                load_percentage,
                threshold,
            )
        else:
            # For warning and emergency alerts, use the structured logging
            logger.warning(
                f"{alert_level.upper()} LOAD ALERT: Service {instance.service_name}:{instance.instance_id} is at {load_percentage:.1%} load (threshold: {threshold:.1%})",
                extra={
                    "service_name": instance.service_name,
                    "instance_id": instance.instance_id,
                    "load_percentage": load_percentage,
                    "threshold": threshold,
                    "alert_level": alert_level,
                    "alert_count": alert_state.alert_count,
                    "alert_type": "load_alert",
                },
            )

    async def _handle_health_check_timeout(self, instance: ServiceInstance):
        """Handle health check timeout"""
        await service_registry.update_service_health(
            instance.service_name, instance.instance_id, ServiceStatus.UNHEALTHY
        )
        log_health_check_failure(
            logger,
            instance.service_name,
            instance.instance_id,
            "timeout",
            instance.health_endpoint,
        )

    async def _handle_health_check_error(
        self, instance: ServiceInstance, error: Exception
    ):
        """Handle health check error"""
        await service_registry.update_service_health(
            instance.service_name, instance.instance_id, ServiceStatus.UNHEALTHY
        )
        log_health_check_failure(
            logger,
            instance.service_name,
            instance.instance_id,
            str(error),
            instance.health_endpoint,
        )

    async def _cleanup_expired_services(self):
        """Remove services that haven't sent heartbeat within TTL"""
        removed_count = await service_registry.cleanup_expired_services(
            SERVICE_REGISTRATION_TTL_SECONDS
        )
        if removed_count > 0:
            logger.info(f"Cleaned up {removed_count} expired services")

    def _log_monitoring_stats(self):
        """Log monitoring statistics"""
        stats = self._monitoring_stats
        success_rate = (
            (stats["successful_checks"] / stats["total_checks"] * 100)
            if stats["total_checks"] > 0
            else 0
        )

        logger.info(
            "Health monitoring statistics",
            extra={
                "total_checks": stats["total_checks"],
                "successful_checks": stats["successful_checks"],
                "failed_checks": stats["failed_checks"],
                "success_rate_percent": round(success_rate, 2),
                "critical_alerts": stats["critical_alerts"],
                "warning_alerts": stats["warning_alerts"],
                "emergency_alerts": stats["emergency_alerts"],
                "event_type": "monitoring_stats",
            },
        )

    def get_monitoring_stats(self) -> dict:
        """Get current monitoring statistics"""
        return self._monitoring_stats.copy()

    def get_alert_states(self) -> Dict[str, AlertState]:
        """Get current alert states"""
        return self._alert_states.copy()

    def reset_stats(self):
        """Reset monitoring statistics"""
        self._monitoring_stats = {
            "total_checks": 0,
            "successful_checks": 0,
            "failed_checks": 0,
            "critical_alerts": 0,
            "warning_alerts": 0,
            "emergency_alerts": 0,
        }

    def is_monitoring_enabled(self) -> bool:
        """Check if monitoring is enabled"""
        return MONITORING_ENABLED and self._running


# Global health monitor instance
health_monitor = HealthMonitor()
