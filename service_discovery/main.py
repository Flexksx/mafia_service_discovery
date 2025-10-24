from contextlib import asynccontextmanager
from fastapi import FastAPI

from service_discovery.api import api_router
from service_discovery.service_registration.health_monitor import health_monitor
from service_discovery.config import (
    LOG_LEVEL,
    LOG_FORMAT_TYPE,
    LOG_ENABLE_CONSOLE,
    LOG_ENABLE_FILE,
    LOG_FILE_PATH,
)
from service_discovery.logger_config import ServiceDiscoveryLogger

# Configure logging
ServiceDiscoveryLogger.setup_logging(
    level=LOG_LEVEL,
    format_type=LOG_FORMAT_TYPE,
    enable_console=LOG_ENABLE_CONSOLE,
    enable_file=LOG_ENABLE_FILE,
    log_file_path=LOG_FILE_PATH,
)

logger = ServiceDiscoveryLogger.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("Starting Service Discovery Service...")

    # Start health monitoring
    await health_monitor.start_monitoring()

    try:
        logger.info("Service Discovery Service started successfully")
        yield
    finally:
        # Stop health monitoring
        await health_monitor.stop_monitoring()
        logger.info("Service Discovery Service stopped")


app = FastAPI(
    title="Service Discovery Service",
    description="Service discovery and health monitoring for Mafia Platform",
    version="0.1.0",
    lifespan=lifespan,
)

# Include API routers
app.include_router(api_router)


@app.get("/")
def root():
    return {"message": "Service Discovery is running 🔍"}


@app.get("/health")
def health_check():
    """Health check endpoint for the service discovery itself"""
    return {
        "status": "healthy",
        "service": "service-discovery",
        "load_percentage": 0.0,  # Service discovery should have minimal load
    }


def main():
    """Main entry point for the service"""
    import uvicorn
    from service_discovery.config import SERVICE_DISCOVERY_HOST, SERVICE_DISCOVERY_PORT

    uvicorn.run(
        "service_discovery.main:app",
        host=SERVICE_DISCOVERY_HOST,
        port=SERVICE_DISCOVERY_PORT,
        reload=False,
        log_level=LOG_LEVEL.lower(),
    )


if __name__ == "__main__":
    main()
