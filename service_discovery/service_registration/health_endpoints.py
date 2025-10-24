from fastapi import APIRouter

from service_discovery.service_registration.health_utils import HealthChecker


def create_health_check_endpoint(health_checker: HealthChecker):
    """Create a FastAPI health check endpoint"""
    router = APIRouter()

    @router.get("/health")
    async def health_check():
        """Health check endpoint for service discovery"""
        return await health_checker.check_health()

    return router


def setup_service_health_checks(
    app, service_name: str, db_client=None, external_services=None
):
    """Setup health checks for a FastAPI service"""
    from service_discovery.service_registration.health_utils import (
        DatabaseHealthCheck,
        ExternalServiceHealthCheck,
    )

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
