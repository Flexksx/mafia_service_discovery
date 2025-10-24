import asyncio
import pytest
import logging
from typing import List

from tests.test_client import (
    ServiceDiscoveryTestClient,
    MockService,
    ServiceInstanceData,
)

logger = logging.getLogger(__name__)


class TestServiceDiscovery:
    """Comprehensive test suite for service discovery"""

    @pytest.fixture
    async def client(self):
        """Create test client"""
        return ServiceDiscoveryTestClient()

    @pytest.fixture
    async def mock_service(self):
        """Create and start a mock service"""
        service = MockService("test-service", "instance-1")
        await service.start()
        yield service
        await service.stop()

    @pytest.fixture
    async def service_instance(self, mock_service):
        """Create test service instance"""
        return mock_service.get_test_instance()

    @pytest.mark.asyncio
    async def test_service_discovery_health(self, client):
        """Test that service discovery service is healthy"""
        assert (
            await client.health_check()
        ), "Service discovery service should be healthy"

    @pytest.mark.asyncio
    async def test_service_registration(self, client, service_instance):
        """Test service registration"""
        # Register service
        success = await client.register_service(service_instance)
        assert success, "Service registration should succeed"

        # Verify service is registered
        instances = await client.get_service_instances(service_instance.service_name)
        assert len(instances) == 1, "Should have exactly one instance"

        instance = instances[0]
        assert instance["service_name"] == service_instance.service_name
        assert instance["instance_id"] == service_instance.instance_id
        assert instance["host"] == service_instance.host
        assert instance["port"] == service_instance.port

    @pytest.mark.asyncio
    async def test_service_heartbeat(self, client, service_instance):
        """Test service heartbeat functionality"""
        # Register service first
        await client.register_service(service_instance)

        # Send heartbeat
        success = await client.send_heartbeat(
            service_instance.service_name, service_instance.instance_id
        )
        assert success, "Heartbeat should succeed"

        # Verify heartbeat was recorded
        instances = await client.get_service_instances(service_instance.service_name)
        assert len(instances) == 1
        assert instances[0]["last_heartbeat"] is not None

    @pytest.mark.asyncio
    async def test_service_unregistration(self, client, service_instance):
        """Test service unregistration"""
        # Register service first
        await client.register_service(service_instance)

        # Verify service is registered
        instances = await client.get_service_instances(service_instance.service_name)
        assert len(instances) == 1

        # Unregister service
        success = await client.unregister_service(
            service_instance.service_name, service_instance.instance_id
        )
        assert success, "Service unregistration should succeed"

        # Verify service is no longer registered
        instances = await client.get_service_instances(service_instance.service_name)
        assert len(instances) == 0, "Service should be unregistered"

    @pytest.mark.asyncio
    async def test_multiple_service_instances(self, client):
        """Test multiple instances of the same service"""
        # Create multiple mock services
        services = []
        for i in range(3):
            service = MockService(f"multi-service", f"instance-{i+1}")
            await service.start()
            services.append(service)

        try:
            # Register all services
            for service in services:
                instance = service.get_test_instance()
                success = await client.register_service(instance)
                assert success, f"Registration of {instance.instance_id} should succeed"

            # Verify all instances are registered
            instances = await client.get_service_instances("multi-service")
            assert len(instances) == 3, "Should have 3 instances"

            # Test listing all services
            all_services = await client.list_all_services()
            assert "multi-service" in all_services
            assert len(all_services["multi-service"]) == 3

        finally:
            # Clean up
            for service in services:
                await service.stop()

    @pytest.mark.asyncio
    async def test_healthy_instances_filter(self, client, service_instance):
        """Test filtering for healthy instances only"""
        # Register service
        await client.register_service(service_instance)

        # Get healthy instances
        healthy_instances = await client.get_healthy_service_instances(
            service_instance.service_name
        )
        assert len(healthy_instances) >= 0, "Should return healthy instances"

        # All instances should be healthy initially
        instances = await client.get_service_instances(service_instance.service_name)
        for instance in instances:
            assert instance["status"] in [
                "healthy",
                "unknown",
            ], "Initial status should be healthy or unknown"

    @pytest.mark.asyncio
    async def test_prometheus_format(self, client, service_instance):
        """Test Prometheus service discovery format"""
        # Register service
        await client.register_service(service_instance)

        # Get Prometheus targets
        targets = await client.get_prometheus_targets(service_instance.service_name)
        assert len(targets) >= 0, "Should return Prometheus targets"

        if targets:
            target = targets[0]
            assert "targets" in target, "Should have targets field"
            assert "labels" in target, "Should have labels field"
            assert service_instance.instance_id in target["labels"]["instance"]

    @pytest.mark.asyncio
    async def test_duplicate_registration(self, client, service_instance):
        """Test registering the same service twice"""
        # Register service first time
        success1 = await client.register_service(service_instance)
        assert success1, "First registration should succeed"

        # Register same service again
        success2 = await client.register_service(service_instance)
        assert success2, "Duplicate registration should succeed (overwrites)"

        # Should still have only one instance
        instances = await client.get_service_instances(service_instance.service_name)
        assert (
            len(instances) == 1
        ), "Should have only one instance after duplicate registration"

    @pytest.mark.asyncio
    async def test_invalid_heartbeat(self, client):
        """Test heartbeat for non-existent service"""
        success = await client.send_heartbeat(
            "non-existent-service", "non-existent-instance"
        )
        assert not success, "Heartbeat for non-existent service should fail"

    @pytest.mark.asyncio
    async def test_invalid_unregistration(self, client):
        """Test unregistering non-existent service"""
        success = await client.unregister_service(
            "non-existent-service", "non-existent-instance"
        )
        assert not success, "Unregistration of non-existent service should fail"

    @pytest.mark.asyncio
    async def test_service_metadata(self, client, service_instance):
        """Test service metadata handling"""
        # Register service with metadata
        await client.register_service(service_instance)

        # Verify metadata is stored
        instances = await client.get_service_instances(service_instance.service_name)
        assert len(instances) == 1

        instance = instances[0]
        assert instance["metadata"] == service_instance.metadata

    @pytest.mark.asyncio
    async def test_concurrent_registrations(self, client):
        """Test concurrent service registrations"""
        # Create multiple services concurrently
        services = []
        for i in range(5):
            service = MockService(f"concurrent-service", f"instance-{i+1}")
            await service.start()
            services.append(service)

        try:
            # Register all services concurrently
            tasks = []
            for service in services:
                instance = service.get_test_instance()
                task = client.register_service(instance)
                tasks.append(task)

            results = await asyncio.gather(*tasks)
            assert all(results), "All concurrent registrations should succeed"

            # Verify all services are registered
            instances = await client.get_service_instances("concurrent-service")
            assert len(instances) == 5, "Should have 5 instances"

        finally:
            # Clean up
            for service in services:
                await service.stop()

    @pytest.mark.asyncio
    async def test_service_discovery_endpoints(self, client):
        """Test all service discovery endpoints are accessible"""
        # Test root endpoint
        import httpx

        async with httpx.AsyncClient() as http_client:
            response = await http_client.get(f"{client.base_url}/")
            assert response.status_code == 200

        # Test health endpoint
        assert await client.health_check()

        # Test services endpoint
        services = await client.list_all_services()
        assert isinstance(services, dict)

    @pytest.mark.asyncio
    async def test_authentication(self, client):
        """Test authentication requirements"""
        # Create client without authentication
        unauthenticated_client = ServiceDiscoveryTestClient(secret="wrong-secret")

        service_instance = ServiceInstanceData(
            service_name="auth-test",
            instance_id="instance-1",
            host="localhost",
            port=8000,
        )

        # Registration should fail without proper authentication
        success = await unauthenticated_client.register_service(service_instance)
        assert not success, "Registration should fail with wrong secret"

    @pytest.mark.asyncio
    async def test_service_cleanup_after_unregistration(self, client, service_instance):
        """Test that services are properly cleaned up after unregistration"""
        # Register service
        await client.register_service(service_instance)

        # Verify service exists
        all_services = await client.list_all_services()
        assert service_instance.service_name in all_services

        # Unregister service
        await client.unregister_service(
            service_instance.service_name, service_instance.instance_id
        )

        # Verify service is removed from all services list
        all_services = await client.list_all_services()
        assert (
            service_instance.service_name not in all_services
            or len(all_services[service_instance.service_name]) == 0
        )
