# Service Discovery Service

A service discovery and health monitoring service for the Mafia Platform.

## Features

- **Service Registration**: Services can register themselves on startup
- **Health Monitoring**: Periodic health checks with load monitoring
- **Critical Load Alerts**: Automatic alerting when services reach critical load levels
- **In-Memory Database**: Fast, in-memory service registry
- **Heartbeat Management**: Services send heartbeats to maintain registration
- **Service Discovery**: Query endpoints to find healthy service instances

## Architecture

The service follows the same modular architecture as the gateway service:

- `config.py` - Configuration management
- `registry.py` - In-memory service registry
- `health_monitor.py` - Health checking and monitoring
- `routers.py` - API endpoints for service registration and discovery
- `main.py` - FastAPI application and startup logic

## API Endpoints

### Service Registration
- `POST /v1/discovery/register` - Register a new service instance
- `POST /v1/discovery/heartbeat` - Update service heartbeat
- `DELETE /v1/discovery/unregister/{service_name}/{instance_id}` - Unregister service

### Service Discovery
- `GET /v1/discovery/services` - List all registered services
- `GET /v1/discovery/services/{service_name}` - Get instances of a specific service
- `GET /v1/discovery/services/{service_name}/healthy` - Get only healthy instances

### Health Check
- `GET /health` - Health check endpoint for the service discovery itself

## Configuration

Environment variables:

- `SERVICE_DISCOVERY_PORT` - Port to run on (default: 3004)
- `SERVICE_DISCOVERY_HOST` - Host to bind to (default: 0.0.0.0)
- `HEALTH_CHECK_INTERVAL_SECONDS` - Health check interval (default: 30)
- `HEALTH_CHECK_TIMEOUT_SECONDS` - Health check timeout (default: 5)
- `CRITICAL_LOAD_THRESHOLD` - Critical load threshold (default: 0.8)
- `SERVICE_REGISTRATION_TTL_SECONDS` - Service TTL (default: 300)
- `SERVICE_HEARTBEAT_INTERVAL_SECONDS` - Heartbeat interval (default: 60)
- `LOG_LEVEL` - Logging level (default: INFO)
- `SERVICE_DISCOVERY_SECRET` - Secret for internal communication

## Usage

### Registering a Service

```python
import httpx

async def register_service():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://service-discovery:3004/v1/discovery/register",
            json={
                "service_name": "my-service",
                "instance_id": "instance-1",
                "host": "localhost",
                "port": 8080,
                "health_endpoint": "/health",
                "metadata": {"version": "1.0.0"}
            },
            headers={"Authorization": f"Bearer {SERVICE_DISCOVERY_SECRET}"}
        )
        return response.json()
```

### Sending Heartbeats

```python
async def send_heartbeat():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://service-discovery:3004/v1/discovery/heartbeat",
            json={
                "service_name": "my-service",
                "instance_id": "instance-1"
            },
            headers={"Authorization": f"Bearer {SERVICE_DISCOVERY_SECRET}"}
        )
        return response.json()
```

### Discovering Services

```python
async def discover_services():
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "http://service-discovery:3004/v1/discovery/services/my-service/healthy"
        )
        return response.json()
```

## Health Check Format

Services should implement a health check endpoint that returns:

```json
{
    "status": "healthy",
    "load_percentage": 0.3
}
```

The `load_percentage` field should be a number between 0.0 and 1.0 representing the current load on the service.
