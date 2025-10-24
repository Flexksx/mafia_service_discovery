import asyncio
import logging
import psutil
from typing import Dict, Any, Optional
from datetime import datetime

from service_discovery.types import HealthCheckResult
from service_discovery.constants import (
    CPU_WEIGHT,
    MEMORY_WEIGHT,
    DISK_WEIGHT,
    MAX_LOAD_PERCENTAGE,
    STATUS_HEALTHY,
    STATUS_UNHEALTHY,
)

logger = logging.getLogger(__name__)


class HealthChecker:
    """Health checker for service instances"""

    def __init__(self, service_name: str):
        self.service_name = service_name
        self.start_time = datetime.now()
        self._custom_checks: Dict[str, callable] = {}

    def add_custom_check(self, name: str, check_func: callable):
        """Add a custom health check function"""
        self._custom_checks[name] = check_func

    def get_system_load(self) -> float:
        """Get current system load percentage"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory_percent = psutil.virtual_memory().percent
            disk_percent = psutil.disk_usage("/").percent

            overall_load = (
                cpu_percent * CPU_WEIGHT
                + memory_percent * MEMORY_WEIGHT
                + disk_percent * DISK_WEIGHT
            ) / 100

            return min(overall_load, MAX_LOAD_PERCENTAGE)
        except Exception as e:
            logger.warning(f"Failed to get system load: {e}")
            return 0.0

    async def check_health(self) -> HealthCheckResult:
        """Perform comprehensive health check"""
        health_status = {
            "status": STATUS_HEALTHY,
            "service": self.service_name,
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": (datetime.now() - self.start_time).total_seconds(),
            "load_percentage": self.get_system_load(),
        }

        custom_results = await self._run_custom_checks()
        if custom_results:
            health_status["custom_checks"] = custom_results
            if not all(
                check["status"] == STATUS_HEALTHY for check in custom_results.values()
            ):
                health_status["status"] = STATUS_UNHEALTHY

        return HealthCheckResult(**health_status)

    async def _run_custom_checks(self) -> Optional[Dict[str, Dict[str, Any]]]:
        """Run all custom health checks"""
        if not self._custom_checks:
            return None

        custom_results = {}
        for name, check_func in self._custom_checks.items():
            try:
                result = await self._execute_check(check_func)
                custom_results[name] = {
                    "status": STATUS_HEALTHY if result else STATUS_UNHEALTHY,
                    "result": result,
                }
            except Exception as e:
                logger.error(f"Custom health check '{name}' failed: {e}")
                custom_results[name] = {"status": STATUS_UNHEALTHY, "error": str(e)}

        return custom_results

    async def _execute_check(self, check_func: callable) -> Any:
        """Execute a single health check function"""
        if asyncio.iscoroutinefunction(check_func):
            return await check_func()
        return check_func()


class DatabaseHealthCheck:
    """Health check for database connectivity"""

    def __init__(self, db_client):
        self.db_client = db_client

    async def check_database(self) -> bool:
        """Check if database is accessible"""
        try:
            await self.db_client.execute("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False


class ExternalServiceHealthCheck:
    """Health check for external service dependencies"""

    def __init__(self, service_url: str):
        self.service_url = service_url

    async def check_external_service(self) -> bool:
        """Check if external service is accessible"""
        try:
            import httpx

            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.service_url}/health")
                return response.status_code == 200
        except Exception as e:
            logger.error(f"External service health check failed: {e}")
            return False
