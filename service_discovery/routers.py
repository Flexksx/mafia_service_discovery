from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
from typing import Dict, List, Optional
from datetime import datetime
import logging

from service_discovery.registry import service_registry, ServiceInstance, ServiceStatus
from service_discovery.config import SERVICE_DISCOVERY_SECRET

logger = logging.getLogger(__name__)

router = APIRouter()


class ServiceRegistrationRequest(BaseModel):
    service_name: str
    instance_id: str
    host: str
    port: int
    health_endpoint: str = "/health"
    metadata: Dict[str, str] = {}


class ServiceRegistrationResponse(BaseModel):
    success: bool
    message: str


class ServiceHeartbeatRequest(BaseModel):
    service_name: str
    instance_id: str


class ServiceHeartbeatResponse(BaseModel):
    success: bool
    message: str


class ServiceInstanceResponse(BaseModel):
    service_name: str
    instance_id: str
    host: str
    port: int
    health_endpoint: str
    status: str
    last_health_check: Optional[datetime]
    last_heartbeat: Optional[datetime]
    load_percentage: float
    metadata: Dict[str, str]
    registered_at: datetime


class ServiceListResponse(BaseModel):
    services: Dict[str, List[ServiceInstanceResponse]]


def verify_service_secret(authorization: str = Header(None)) -> bool:
    """Verify service discovery secret for internal communication"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401, detail="Invalid Authorization header format"
        )

    secret = authorization[7:]  # Remove "Bearer " prefix

    if secret != SERVICE_DISCOVERY_SECRET:
        raise HTTPException(status_code=401, detail="Invalid service discovery secret")
    return True


@router.post("/register", response_model=ServiceRegistrationResponse)
async def register_service(
    request: ServiceRegistrationRequest, secret: str = Depends(verify_service_secret)
):
    """Register a new service instance"""
    try:
        service_instance = ServiceInstance(
            service_name=request.service_name,
            instance_id=request.instance_id,
            host=request.host,
            port=request.port,
            health_endpoint=request.health_endpoint,
            metadata=request.metadata,
        )

        success = await service_registry.register_service(service_instance)

        if success:
            logger.info(
                f"Service registered: {request.service_name}:{request.instance_id}"
            )
            return ServiceRegistrationResponse(
                success=True,
                message=f"Service {request.service_name}:{request.instance_id} registered successfully",
            )
        else:
            return ServiceRegistrationResponse(
                success=False, message="Failed to register service"
            )

    except Exception as e:
        logger.error(f"Error registering service: {e}")
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")


@router.post("/heartbeat", response_model=ServiceHeartbeatResponse)
async def service_heartbeat(
    request: ServiceHeartbeatRequest, secret: str = Depends(verify_service_secret)
):
    """Update service heartbeat"""
    try:
        success = await service_registry.update_heartbeat(
            request.service_name, request.instance_id
        )

        if success:
            return ServiceHeartbeatResponse(
                success=True, message="Heartbeat updated successfully"
            )
        else:
            return ServiceHeartbeatResponse(success=False, message="Service not found")

    except Exception as e:
        logger.error(f"Error updating heartbeat: {e}")
        raise HTTPException(
            status_code=500, detail=f"Heartbeat update failed: {str(e)}"
        )


@router.delete("/unregister/{service_name}/{instance_id}")
async def unregister_service(
    service_name: str, instance_id: str, secret: str = Depends(verify_service_secret)
):
    """Unregister a service instance"""
    try:
        success = await service_registry.unregister_service(service_name, instance_id)

        if success:
            return {"success": True, "message": "Service unregistered successfully"}
        else:
            raise HTTPException(status_code=404, detail="Service not found")

    except Exception as e:
        logger.error(f"Error unregistering service: {e}")
        raise HTTPException(status_code=500, detail=f"Unregistration failed: {str(e)}")


@router.get("/services", response_model=ServiceListResponse)
async def list_all_services():
    """List all registered services"""
    try:
        all_services = await service_registry.get_all_services()

        response_data = {}
        for service_name, instances in all_services.items():
            response_data[service_name] = [
                ServiceInstanceResponse(
                    service_name=instance.service_name,
                    instance_id=instance.instance_id,
                    host=instance.host,
                    port=instance.port,
                    health_endpoint=instance.health_endpoint,
                    status=instance.status.value,
                    last_health_check=instance.last_health_check,
                    last_heartbeat=instance.last_heartbeat,
                    load_percentage=instance.load_percentage,
                    metadata=instance.metadata,
                    registered_at=instance.registered_at,
                )
                for instance in instances
            ]

        return ServiceListResponse(services=response_data)

    except Exception as e:
        logger.error(f"Error listing services: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to list services: {str(e)}"
        )


@router.get("/services/{service_name}")
async def get_service_instances(service_name: str):
    """Get instances of a specific service"""
    try:
        instances = await service_registry.get_service_instances(service_name)

        if not instances:
            raise HTTPException(
                status_code=404, detail=f"Service '{service_name}' not found"
            )

        return {
            "service_name": service_name,
            "instances": [
                ServiceInstanceResponse(
                    service_name=instance.service_name,
                    instance_id=instance.instance_id,
                    host=instance.host,
                    port=instance.port,
                    health_endpoint=instance.health_endpoint,
                    status=instance.status.value,
                    last_health_check=instance.last_health_check,
                    last_heartbeat=instance.last_heartbeat,
                    load_percentage=instance.load_percentage,
                    metadata=instance.metadata,
                    registered_at=instance.registered_at,
                )
                for instance in instances
            ],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting service instances: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get service instances: {str(e)}"
        )


@router.get("/services/{service_name}/healthy")
async def get_healthy_service_instances(service_name: str):
    """Get only healthy instances of a specific service"""
    try:
        instances = await service_registry.get_healthy_service_instances(service_name)

        return {
            "service_name": service_name,
            "healthy_instances": [
                ServiceInstanceResponse(
                    service_name=instance.service_name,
                    instance_id=instance.instance_id,
                    host=instance.host,
                    port=instance.port,
                    health_endpoint=instance.health_endpoint,
                    status=instance.status.value,
                    last_health_check=instance.last_health_check,
                    last_heartbeat=instance.last_heartbeat,
                    load_percentage=instance.load_percentage,
                    metadata=instance.metadata,
                    registered_at=instance.registered_at,
                )
                for instance in instances
            ],
        }

    except Exception as e:
        logger.error(f"Error getting healthy service instances: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get healthy service instances: {str(e)}"
        )
