"""
Health check utilities for services that want to register with service discovery

This module provides utilities for implementing health check endpoints
that are compatible with the service discovery health monitoring.
"""

import asyncio
import logging
import psutil
from typing import Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class HealthChecker:
    """Health checker for service instances"""

    def __init__(self, service_name: str):
        self.service_name = service_name
        self.start_time = datetime.now()
        self._custom_checks = {}

    def add_custom_check(self, name: str, check_func):
        """Add a custom health check function"""
        self._custom_checks[name] = check_func

    def get_system_load(self) -> float:
        """Get current system load percentage"""
        try:
            # Get CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)

            # Get memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent

            # Get disk usage
            disk = psutil.disk_usage("/")
            disk_percent = disk.percent

            # Calculate overall load (weighted average)
            # CPU: 50%, Memory: 30%, Disk: 20%
            overall_load = (
                cpu_percent * 0.5 + memory_percent * 0.3 + disk_percent * 0.2
            ) / 100

            return min(overall_load, 1.0)  # Cap at 100%

        except Exception as e:
            logger.warning(f"Failed to get system load: {e}")
            return 0.0

    async def check_health(self) -> Dict[str, Any]:
        """Perform comprehensive health check"""
        health_status = {
            "status": "healthy",
            "service": self.service_name,
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": (datetime.now() - self.start_time).total_seconds(),
            "load_percentage": self.get_system_load(),
        }

        # Run custom checks
        custom_results = {}
        for name, check_func in self._custom_checks.items():
            try:
                if asyncio.iscoroutinefunction(check_func):
                    result = await check_func()
                else:
                    result = check_func()

                custom_results[name] = {
                    "status": "healthy" if result else "unhealthy",
                    "result": result,
                }

                # If any custom check fails, mark overall status as unhealthy
                if not result:
                    health_status["status"] = "unhealthy"

            except Exception as e:
                logger.error(f"Custom health check '{name}' failed: {e}")
                custom_results[name] = {"status": "unhealthy", "error": str(e)}
                health_status["status"] = "unhealthy"

        if custom_results:
            health_status["custom_checks"] = custom_results

        return health_status


def create_health_check_endpoint(health_checker: HealthChecker):
    """Create a FastAPI health check endpoint"""
    from fastapi import APIRouter

    router = APIRouter()

    @router.get("/health")
    async def health_check():
        """Health check endpoint for service discovery"""
        return await health_checker.check_health()

    return router


# Example usage for different types of services
class DatabaseHealthCheck:
    """Example health check for database connectivity"""

    def __init__(self, db_client):
        self.db_client = db_client

    async def check_database(self) -> bool:
        """Check if database is accessible"""
        try:
            # Example: ping the database
            await self.db_client.execute("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False


class ExternalServiceHealthCheck:
    """Example health check for external service dependencies"""

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


# Example implementation for a FastAPI service
def setup_service_health_checks(
    app, service_name: str, db_client=None, external_services=None
):
    """Setup health checks for a FastAPI service"""
    health_checker = HealthChecker(service_name)

    # Add database check if provided
    if db_client:
        db_check = DatabaseHealthCheck(db_client)
        health_checker.add_custom_check("database", db_check.check_database)

    # Add external service checks if provided
    if external_services:
        for service_name, service_url in external_services.items():
            external_check = ExternalServiceHealthCheck(service_url)
            health_checker.add_custom_check(
                f"external_{service_name}", external_check.check_external_service
            )

    # Create and include health check router
    health_router = create_health_check_endpoint(health_checker)
    app.include_router(health_router)

    return health_checker
