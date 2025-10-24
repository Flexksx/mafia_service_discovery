from fastapi import APIRouter

from service_discovery.api.routes import router as discovery_router

# Main API router that includes all sub-routers
api_router = APIRouter()

# Include discovery routes with prefix
api_router.include_router(
    discovery_router, prefix="/v1/discovery", tags=["Service Discovery"]
)
