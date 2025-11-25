"""
Integration tests for grpc_port and instance_url fields
Tests the full flow from registration to retrieval
"""
import pytest
import httpx
import asyncio
from service_discovery.service_registration.registry import ServiceRegistry
from service_discovery.types import ServiceInstance, ServiceStatus


@pytest.mark.asyncio
class TestGrpcPortIntegration:
    """Integration tests for grpc_port field"""

    async def test_register_and_retrieve_service_with_grpc_port(self):
        """Test registering and retrieving a service with grpc_port"""
        registry = ServiceRegistry()
        
        # Register service with grpc_port
        instance = ServiceInstance(
            service_name="grpc-service",
            instance_id="grpc-1",
            host="localhost",
            port=8080,
            grpc_port=50051,
            instance_url="http://localhost:8080",
        )
        
        success = await registry.register_service(instance)
        assert success
        
        # Retrieve instances
        instances = await registry.get_service_instances("grpc-service")
        assert len(instances) == 1
        assert instances[0].grpc_port == 50051

    async def test_register_service_without_grpc_port(self):
        """Test registering a service without grpc_port (backward compatibility)"""
        registry = ServiceRegistry()
        
        # Register service without grpc_port
        instance = ServiceInstance(
            service_name="http-only-service",
            instance_id="http-1",
            host="localhost",
            port=8080,
            instance_url="http://localhost:8080",
        )
        
        success = await registry.register_service(instance)
        assert success
        
        # Retrieve instances
        instances = await registry.get_service_instances("http-only-service")
        assert len(instances) == 1
        assert instances[0].grpc_port is None

    async def test_multiple_instances_with_different_grpc_ports(self):
        """Test multiple instances with different grpc_ports"""
        registry = ServiceRegistry()
        
        # Register multiple instances
        instance1 = ServiceInstance(
            service_name="multi-service",
            instance_id="multi-1",
            host="localhost",
            port=8080,
            grpc_port=50051,
            instance_url="http://localhost:8080",
        )
        instance2 = ServiceInstance(
            service_name="multi-service",
            instance_id="multi-2",
            host="localhost",
            port=8081,
            grpc_port=50052,
            instance_url="http://localhost:8081",
        )
        
        await registry.register_service(instance1)
        await registry.register_service(instance2)
        
        # Retrieve instances
        instances = await registry.get_service_instances("multi-service")
        assert len(instances) == 2
        
        grpc_ports = {inst.instance_id: inst.grpc_port for inst in instances}
        assert grpc_ports["multi-1"] == 50051
        assert grpc_ports["multi-2"] == 50052


@pytest.mark.asyncio
class TestInstanceUrlIntegration:
    """Integration tests for instance_url field"""

    async def test_register_and_retrieve_service_with_instance_url(self):
        """Test registering and retrieving a service with custom instance_url"""
        registry = ServiceRegistry()
        
        # Register service with custom instance_url
        instance = ServiceInstance(
            service_name="custom-url-service",
            instance_id="custom-1",
            host="internal-host",
            port=8080,
            instance_url="https://external-domain.com:443",
        )
        
        success = await registry.register_service(instance)
        assert success
        
        # Retrieve instances
        instances = await registry.get_service_instances("custom-url-service")
        assert len(instances) == 1
        assert instances[0].instance_url == "https://external-domain.com:443"

    async def test_auto_generated_instance_url(self):
        """Test that instance_url is auto-generated from host and port"""
        registry = ServiceRegistry()
        
        # Register service without explicit instance_url
        instance = ServiceInstance(
            service_name="auto-url-service",
            instance_id="auto-1",
            host="game-service",
            port=9000,
        )
        
        success = await registry.register_service(instance)
        assert success
        
        # Retrieve instances
        instances = await registry.get_service_instances("auto-url-service")
        assert len(instances) == 1
        assert instances[0].instance_url == "http://game-service:9000"

    async def test_instance_url_preserved_across_operations(self):
        """Test that instance_url is preserved across registry operations"""
        registry = ServiceRegistry()
        
        # Register service
        instance = ServiceInstance(
            service_name="preserve-service",
            instance_id="preserve-1",
            host="localhost",
            port=8080,
            instance_url="https://custom.com:8443",
            grpc_port=50051,
        )
        
        await registry.register_service(instance)
        
        # Update health status
        await registry.update_service_health(
            "preserve-service",
            "preserve-1",
            ServiceStatus.HEALTHY,
            0.5
        )
        
        # Retrieve and verify instance_url is preserved
        instances = await registry.get_service_instances("preserve-service")
        assert len(instances) == 1
        assert instances[0].instance_url == "https://custom.com:8443"
        assert instances[0].grpc_port == 50051


@pytest.mark.asyncio
class TestCombinedFieldsIntegration:
    """Integration tests for both grpc_port and instance_url together"""

    async def test_full_service_registration(self):
        """Test service registration with all fields including grpc_port and instance_url"""
        registry = ServiceRegistry()
        
        # Register service with all fields
        instance = ServiceInstance(
            service_name="full-featured-service",
            instance_id="full-1",
            host="internal-service.local",
            port=8080,
            instance_url="https://public-api.com:443",
            grpc_port=50051,
            health_endpoint="/api/v1/health",
            metadata={"region": "us-east-1", "version": "2.0"},
            topics=["game.started", "game.ended"],
        )
        
        success = await registry.register_service(instance)
        assert success
        
        # Retrieve and verify all fields
        instances = await registry.get_service_instances("full-featured-service")
        assert len(instances) == 1
        
        retrieved = instances[0]
        assert retrieved.service_name == "full-featured-service"
        assert retrieved.instance_id == "full-1"
        assert retrieved.host == "internal-service.local"
        assert retrieved.port == 8080
        assert retrieved.instance_url == "https://public-api.com:443"
        assert retrieved.grpc_port == 50051
        assert retrieved.health_endpoint == "/api/v1/health"
        assert retrieved.metadata == {"region": "us-east-1", "version": "2.0"}
        assert retrieved.topics == ["game.started", "game.ended"]

    async def test_get_all_services_includes_new_fields(self):
        """Test that get_all_services includes grpc_port and instance_url"""
        registry = ServiceRegistry()
        
        # Register multiple services with different configurations
        instance1 = ServiceInstance(
            service_name="service-a",
            instance_id="a-1",
            host="host-a",
            port=8080,
            instance_url="http://host-a:8080",
            grpc_port=50051,
        )
        instance2 = ServiceInstance(
            service_name="service-b",
            instance_id="b-1",
            host="host-b",
            port=9000,
            instance_url="https://host-b:9443",
        )
        
        await registry.register_service(instance1)
        await registry.register_service(instance2)
        
        # Get all services
        all_services = await registry.get_all_services()
        
        assert "service-a" in all_services
        assert "service-b" in all_services
        
        service_a_instances = all_services["service-a"]
        assert len(service_a_instances) == 1
        assert service_a_instances[0].instance_url == "http://host-a:8080"
        assert service_a_instances[0].grpc_port == 50051
        
        service_b_instances = all_services["service-b"]
        assert len(service_b_instances) == 1
        assert service_b_instances[0].instance_url == "https://host-b:9443"
        assert service_b_instances[0].grpc_port is None

    async def test_healthy_instances_include_new_fields(self):
        """Test that get_healthy_service_instances includes new fields"""
        registry = ServiceRegistry()
        
        # Register service
        instance = ServiceInstance(
            service_name="healthy-service",
            instance_id="healthy-1",
            host="localhost",
            port=8080,
            instance_url="http://localhost:8080",
            grpc_port=50051,
        )
        
        await registry.register_service(instance)
        
        # Update to healthy status
        await registry.update_service_health(
            "healthy-service",
            "healthy-1",
            ServiceStatus.HEALTHY,
            0.3
        )
        
        # Get healthy instances
        healthy = await registry.get_healthy_service_instances("healthy-service")
        assert len(healthy) == 1
        assert healthy[0].instance_url == "http://localhost:8080"
        assert healthy[0].grpc_port == 50051
        assert healthy[0].status == ServiceStatus.HEALTHY


@pytest.mark.asyncio
class TestBackwardCompatibilityIntegration:
    """Integration tests for backward compatibility"""

    async def test_legacy_service_registration(self):
        """Test that services without new fields still work"""
        registry = ServiceRegistry()
        
        # Register service using minimal fields (pre-upgrade style)
        instance = ServiceInstance(
            service_name="legacy-service",
            instance_id="legacy-1",
            host="legacy-host",
            port=8080,
            health_endpoint="/health",
        )
        
        success = await registry.register_service(instance)
        assert success
        
        # Retrieve and verify defaults
        instances = await registry.get_service_instances("legacy-service")
        assert len(instances) == 1
        assert instances[0].instance_url == "http://legacy-host:8080"
        assert instances[0].grpc_port is None

    async def test_mixed_service_registrations(self):
        """Test that old and new style registrations work together"""
        registry = ServiceRegistry()
        
        # Register legacy service (no grpc_port)
        legacy = ServiceInstance(
            service_name="mixed-test",
            instance_id="legacy-1",
            host="localhost",
            port=8080,
        )
        
        # Register modern service (with grpc_port)
        modern = ServiceInstance(
            service_name="mixed-test",
            instance_id="modern-1",
            host="localhost",
            port=8081,
            grpc_port=50051,
        )
        
        await registry.register_service(legacy)
        await registry.register_service(modern)
        
        # Retrieve all instances
        instances = await registry.get_service_instances("mixed-test")
        assert len(instances) == 2
        
        # Verify mixed configuration
        by_id = {inst.instance_id: inst for inst in instances}
        assert by_id["legacy-1"].grpc_port is None
        assert by_id["modern-1"].grpc_port == 50051
        assert by_id["legacy-1"].instance_url == "http://localhost:8080"
        assert by_id["modern-1"].instance_url == "http://localhost:8081"
