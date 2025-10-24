from fastapi import APIRouter, HTTPException, Depends, Header
import logging

from service_discovery.service_registration.registry import service_registry
from service_discovery.types import (
    ServiceRegistrationRequest,
    ServiceRegistrationResponse,
    ServiceHeartbeatRequest,
    ServiceHeartbeatResponse,
    ServiceInstanceResponse,
    ServiceListResponse,
)
from service_discovery.constants import (
    ERROR_MISSING_AUTH_HEADER,
    ERROR_INVALID_AUTH_FORMAT,
    ERROR_INVALID_SECRET,
    ERROR_SERVICE_NOT_FOUND,
    ERROR_REGISTRATION_FAILED,
    ERROR_HEARTBEAT_FAILED,
    SUCCESS_REGISTERED,
    SUCCESS_HEARTBEAT_UPDATED,
    SUCCESS_UNREGISTERED,
    BEARER_PREFIX,
    HTTP_UNAUTHORIZED,
    HTTP_NOT_FOUND,
    HTTP_INTERNAL_SERVER_ERROR,
)
from service_discovery.config import SERVICE_DISCOVERY_SECRET

logger = logging.getLogger(__name__)

router = APIRouter()


def verify_service_secret(authorization: str = Header(None)) -> bool:
    """Verify service discovery secret for internal communication"""
    if not authorization:
        raise HTTPException(
            status_code=HTTP_UNAUTHORIZED, detail=ERROR_MISSING_AUTH_HEADER
        )

    if not authorization.startswith(BEARER_PREFIX):
        raise HTTPException(
            status_code=HTTP_UNAUTHORIZED, detail=ERROR_INVALID_AUTH_FORMAT
        )

    secret = authorization[len(BEARER_PREFIX) :]
    if secret != SERVICE_DISCOVERY_SECRET:
        raise HTTPException(status_code=HTTP_UNAUTHORIZED, detail=ERROR_INVALID_SECRET)
    return True


@router.post("/register", response_model=ServiceRegistrationResponse)
async def register_service(
    request: ServiceRegistrationRequest, secret: str = Depends(verify_service_secret)
):
    """Register a new service instance"""
    try:
        from service_discovery.types import ServiceInstance

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
            message = f"Service {request.service_name}:{request.instance_id} {SUCCESS_REGISTERED}"
            return ServiceRegistrationResponse(success=True, message=message)
        else:
            return ServiceRegistrationResponse(
                success=False, message=ERROR_REGISTRATION_FAILED
            )

    except Exception as e:
        logger.error(f"Error registering service: {e}")
        raise HTTPException(
            status_code=HTTP_INTERNAL_SERVER_ERROR,
            detail=f"{ERROR_REGISTRATION_FAILED}: {str(e)}",
        )


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
                success=True, message=SUCCESS_HEARTBEAT_UPDATED
            )
        else:
            return ServiceHeartbeatResponse(
                success=False, message=ERROR_SERVICE_NOT_FOUND
            )

    except Exception as e:
        logger.error(f"Error updating heartbeat: {e}")
        raise HTTPException(
            status_code=HTTP_INTERNAL_SERVER_ERROR,
            detail=f"{ERROR_HEARTBEAT_FAILED}: {str(e)}",
        )


@router.delete("/unregister/{service_name}/{instance_id}")
async def unregister_service(
    service_name: str, instance_id: str, secret: str = Depends(verify_service_secret)
):
    """Unregister a service instance"""
    try:
        success = await service_registry.unregister_service(service_name, instance_id)

        if success:
            return {"success": True, "message": SUCCESS_UNREGISTERED}
        else:
            raise HTTPException(
                status_code=HTTP_NOT_FOUND, detail=ERROR_SERVICE_NOT_FOUND
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error unregistering service: {e}")
        raise HTTPException(
            status_code=HTTP_INTERNAL_SERVER_ERROR,
            detail=f"Unregistration failed: {str(e)}",
        )


@router.get("/services", response_model=ServiceListResponse)
async def list_all_services():
    """List all registered services"""
    try:
        all_services = await service_registry.get_all_services()
        response_data = {}

        for service_name, instances in all_services.items():
            response_data[service_name] = [
                ServiceInstanceResponse.from_service_instance(instance)
                for instance in instances
            ]

        return ServiceListResponse(services=response_data)

    except Exception as e:
        logger.error(f"Error listing services: {e}")
        raise HTTPException(
            status_code=HTTP_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list services: {str(e)}",
        )


@router.get("/services/{service_name}")
async def get_service_instances(service_name: str):
    """Get instances of a specific service"""
    try:
        instances = await service_registry.get_service_instances(service_name)

        if not instances:
            raise HTTPException(
                status_code=HTTP_NOT_FOUND, detail=f"Service '{service_name}' not found"
            )

        return {
            "service_name": service_name,
            "instances": [
                ServiceInstanceResponse.from_service_instance(instance)
                for instance in instances
            ],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting service instances: {e}")
        raise HTTPException(
            status_code=HTTP_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get service instances: {str(e)}",
        )


@router.get("/services/{service_name}/healthy")
async def get_healthy_service_instances(service_name: str):
    """Get only healthy instances of a specific service"""
    try:
        instances = await service_registry.get_healthy_service_instances(service_name)

        return {
            "service_name": service_name,
            "healthy_instances": [
                ServiceInstanceResponse.from_service_instance(instance)
                for instance in instances
            ],
        }

    except Exception as e:
        logger.error(f"Error getting healthy service instances: {e}")
        raise HTTPException(
            status_code=HTTP_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get healthy service instances: {str(e)}",
        )


@router.get("/services/{service_name}/instances")
async def get_service_instances_for_prometheus(service_name: str):
    """Get service instances in Prometheus HTTP service discovery format"""
    try:
        from service_discovery.types import PrometheusTarget

        instances = await service_registry.get_healthy_service_instances(service_name)

        prometheus_instances = []
        for instance in instances:
            prometheus_instances.append(
                PrometheusTarget(
                    targets=[f"{instance.host}:{instance.port}"],
                    labels={
                        "instance": instance.instance_id,
                        "service_name": instance.service_name,
                        "status": instance.status.value,
                        "load_percentage": str(instance.load_percentage),
                        **instance.metadata,
                    },
                )
            )

        return prometheus_instances

    except Exception as e:
        logger.error(f"Error getting service instances for Prometheus: {e}")
        raise HTTPException(
            status_code=HTTP_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get service instances: {str(e)}",
        )
