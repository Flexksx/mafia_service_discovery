# Service Discovery Test Suite

This directory contains comprehensive tests for the Service Discovery service.

## Test Structure

- `test_client.py` - Test client and mock service implementations
- `test_service_discovery.py` - Main test suite with comprehensive test cases
- `conftest.py` - Pytest configuration and fixtures

## Running Tests

### Option 1: Using the Test Runner Script (Recommended)

```bash
python run_tests.py
```

This script will:
1. Stop any existing docker containers
2. Start the service discovery service in docker
3. Wait for the service to be ready
4. Run all tests
5. Print results and cleanup

### Option 2: Manual Docker + Pytest

```bash
# Start the service discovery service
docker compose up -d --build

# Wait for service to be ready (check http://localhost:3004/health)

# Run tests
python -m pytest tests/ -v

# Stop services
docker compose down
```

## Test Coverage

The test suite covers:

### Core Functionality
- ✅ Service registration
- ✅ Service unregistration  
- ✅ Heartbeat functionality
- ✅ Service discovery (listing services)
- ✅ Health status filtering
- ✅ Prometheus format output

### Edge Cases
- ✅ Duplicate service registration
- ✅ Non-existent service operations
- ✅ Concurrent registrations
- ✅ Multiple service instances
- ✅ Authentication requirements

### Integration Tests
- ✅ End-to-end service lifecycle
- ✅ Mock service interactions
- ✅ Docker container integration
- ✅ Health endpoint monitoring

## Test Dependencies

The tests require:
- `pytest` - Test framework
- `pytest-asyncio` - Async test support
- `httpx` - HTTP client for testing
- `fastapi` - For mock services
- `uvicorn` - For mock service servers

## Mock Services

The test suite includes `MockService` class that creates temporary FastAPI services to simulate real services registering with the service discovery. These services:

- Run on different ports (8001-9000+)
- Provide `/health` endpoints
- Automatically start/stop during tests
- Include realistic metadata

## Configuration

Test configuration is handled in `conftest.py`:
- Service discovery URL: `http://localhost:3004`
- Test secret: `test-secret-key`
- Log level: `INFO`

## Troubleshooting

### Service Not Ready
If tests fail with "service not ready":
1. Check docker logs: `docker compose logs`
2. Verify port 3004 is not in use
3. Check service discovery health: `curl http://localhost:3004/health`

### Port Conflicts
If you get port conflicts:
1. Stop other services using ports 3004, 8001-9000
2. Or modify port ranges in test files

### Authentication Issues
If authentication tests fail:
1. Verify `SERVICE_DISCOVERY_SECRET` matches in docker-compose.yml
2. Check test client secret configuration
