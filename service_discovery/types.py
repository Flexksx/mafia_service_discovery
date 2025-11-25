from datetime import datetime
from typing import Any, Dict, Optional, List
from dataclasses import dataclass, field
from enum import Enum
from pydantic import BaseModel, Field, validator

from service_discovery.constants import (
    STATUS_HEALTHY,
    STATUS_UNHEALTHY,
    STATUS_UNKNOWN,
    DEFAULT_HEALTH_ENDPOINT,
    MAX_LOAD_PERCENTAGE,
)


class ServiceStatus(Enum):
    HEALTHY = STATUS_HEALTHY
    UNHEALTHY = STATUS_UNHEALTHY
    UNKNOWN = STATUS_UNKNOWN


@dataclass
class ServiceInstance:
    service_name: str
    instance_id: str
    host: str
    port: int
    instance_url: str = ""
    grpc_port: Optional[int] = None
    health_endpoint: str = DEFAULT_HEALTH_ENDPOINT
    status: ServiceStatus = ServiceStatus.UNKNOWN
    last_health_check: Optional[datetime] = None
    last_heartbeat: Optional[datetime] = None
    load_percentage: float = 0.0
    metadata: Dict[str, str] = field(default_factory=dict)
    registered_at: datetime = field(default_factory=datetime.now)
    topics: List[str] = field(default_factory=list)

    def __post_init__(self):
        # Auto-generate instance_url if not provided
        if not self.instance_url:
            self.instance_url = f"http://{self.host}:{self.port}"
        if self.load_percentage > MAX_LOAD_PERCENTAGE:
            self.load_percentage = MAX_LOAD_PERCENTAGE


# Pydantic models for API validation
class ServiceRegistrationRequest(BaseModel):
    service_name: str = Field(..., min_length=1, max_length=100)
    instance_id: str = Field(..., min_length=1, max_length=100)
    host: str = Field(..., min_length=1)
    port: int = Field(..., ge=1, le=65535)
    instance_url: Optional[str] = None
    grpc_port: Optional[int] = Field(None, ge=1, le=65535)
    health_endpoint: str = Field(default=DEFAULT_HEALTH_ENDPOINT)
    metadata: Dict[str, str] = Field(default_factory=dict)
    topics: List[str] = Field(default_factory=list)

    @validator("health_endpoint")
    def validate_health_endpoint(cls, v):
        if not v.startswith("/"):
            raise ValueError("Health endpoint must start with /")
        return v

    @validator("instance_url", always=True)
    def validate_instance_url(cls, v, values):
        """Auto-generate instance_url from host and port if not provided"""
        if not v:
            host = values.get('host')
            port = values.get('port')
            if host and port:
                return f"http://{host}:{port}"
        return v


class ServiceRegistrationResponse(BaseModel):
    success: bool
    message: str


class ServiceHeartbeatRequest(BaseModel):
    service_name: str = Field(..., min_length=1)
    instance_id: str = Field(..., min_length=1)


class ServiceHeartbeatResponse(BaseModel):
    success: bool
    message: str


class ServiceInstanceResponse(BaseModel):
    service_name: str
    instance_id: str
    host: str
    port: int
    instance_url: str
    grpc_port: Optional[int]
    health_endpoint: str
    status: str
    last_health_check: Optional[datetime]
    last_heartbeat: Optional[datetime]
    load_percentage: float
    metadata: Dict[str, str]
    registered_at: datetime
    topics: List[str]

    @classmethod
    def from_service_instance(
        cls, instance: ServiceInstance
    ) -> "ServiceInstanceResponse":
        return cls(
            service_name=instance.service_name,
            instance_id=instance.instance_id,
            host=instance.host,
            port=instance.port,
            instance_url=instance.instance_url,
            grpc_port=instance.grpc_port,
            health_endpoint=instance.health_endpoint,
            status=instance.status.value,
            last_health_check=instance.last_health_check,
            last_heartbeat=instance.last_heartbeat,
            load_percentage=instance.load_percentage,
            metadata=instance.metadata,
            registered_at=instance.registered_at,
            topics=instance.topics,
        )


class ServiceListResponse(BaseModel):
    services: Dict[str, List[ServiceInstanceResponse]]


class HealthCheckResult(BaseModel):
    status: str
    service: str
    timestamp: str
    uptime_seconds: float
    load_percentage: float
    custom_checks: Optional[Dict[str, Dict[str, Any]]] = None


class PrometheusTarget(BaseModel):
    targets: List[str]
    labels: Dict[str, str]


class TopicSubscription(BaseModel):
    """Represents a topic and its subscribed services"""
    topic: str
    services: List[str]


class TopicListResponse(BaseModel):
    """Response model for GET /services/topics endpoint"""
    topics: List[TopicSubscription]

