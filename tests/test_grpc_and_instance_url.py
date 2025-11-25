"""
Tests for grpc_port and instance_url fields in Service Discovery
"""
import pytest
from service_discovery.types import (
    ServiceInstance,
    ServiceRegistrationRequest,
    ServiceInstanceResponse,
)


class TestInstanceUrlField:
    """Test cases for instance_url field"""

    def test_instance_url_auto_generated_from_host_and_port(self):
        """Test that instance_url is auto-generated from host and port"""
        request = ServiceRegistrationRequest(
            service_name="test-service",
            instance_id="test-1",
            host="localhost",
            port=8080,
        )
        assert request.instance_url == "http://localhost:8080"

    def test_instance_url_auto_generated_with_domain(self):
        """Test instance_url generation with domain name"""
        request = ServiceRegistrationRequest(
            service_name="test-service",
            instance_id="test-1",
            host="game-service.local",
            port=9000,
        )
        assert request.instance_url == "http://game-service.local:9000"

    def test_instance_url_explicit_override(self):
        """Test that explicit instance_url overrides auto-generation"""
        request = ServiceRegistrationRequest(
            service_name="test-service",
            instance_id="test-1",
            host="localhost",
            port=8080,
            instance_url="https://custom-domain.com:9000",
        )
        assert request.instance_url == "https://custom-domain.com:9000"

    def test_instance_url_https_protocol(self):
        """Test instance_url with HTTPS protocol"""
        request = ServiceRegistrationRequest(
            service_name="test-service",
            instance_id="test-1",
            host="localhost",
            port=8080,
            instance_url="https://localhost:8443",
        )
        assert request.instance_url == "https://localhost:8443"

    def test_service_instance_auto_generates_url(self):
        """Test ServiceInstance auto-generates instance_url in __post_init__"""
        instance = ServiceInstance(
            service_name="test-service",
            instance_id="test-1",
            host="localhost",
            port=8080,
        )
        assert instance.instance_url == "http://localhost:8080"

    def test_service_instance_with_explicit_url(self):
        """Test ServiceInstance with explicit instance_url"""
        instance = ServiceInstance(
            service_name="test-service",
            instance_id="test-1",
            host="localhost",
            port=8080,
            instance_url="https://custom-url.com:9000",
        )
        assert instance.instance_url == "https://custom-url.com:9000"


class TestGrpcPortField:
    """Test cases for grpc_port field"""

    def test_grpc_port_none_by_default(self):
        """Test that grpc_port is None by default (backward compatibility)"""
        request = ServiceRegistrationRequest(
            service_name="test-service",
            instance_id="test-1",
            host="localhost",
            port=8080,
        )
        assert request.grpc_port is None

    def test_grpc_port_valid_value(self):
        """Test grpc_port with valid port number"""
        request = ServiceRegistrationRequest(
            service_name="test-service",
            instance_id="test-1",
            host="localhost",
            port=8080,
            grpc_port=50051,
        )
        assert request.grpc_port == 50051

    def test_grpc_port_minimum_valid(self):
        """Test grpc_port with minimum valid port (1)"""
        request = ServiceRegistrationRequest(
            service_name="test-service",
            instance_id="test-1",
            host="localhost",
            port=8080,
            grpc_port=1,
        )
        assert request.grpc_port == 1

    def test_grpc_port_maximum_valid(self):
        """Test grpc_port with maximum valid port (65535)"""
        request = ServiceRegistrationRequest(
            service_name="test-service",
            instance_id="test-1",
            host="localhost",
            port=8080,
            grpc_port=65535,
        )
        assert request.grpc_port == 65535

    def test_grpc_port_invalid_too_low(self):
        """Test grpc_port with invalid port (too low)"""
        with pytest.raises(Exception):  # Pydantic validation error
            ServiceRegistrationRequest(
                service_name="test-service",
                instance_id="test-1",
                host="localhost",
                port=8080,
                grpc_port=0,
            )

    def test_grpc_port_invalid_too_high(self):
        """Test grpc_port with invalid port (too high)"""
        with pytest.raises(Exception):  # Pydantic validation error
            ServiceRegistrationRequest(
                service_name="test-service",
                instance_id="test-1",
                host="localhost",
                port=8080,
                grpc_port=65536,
            )

    def test_service_instance_with_grpc_port(self):
        """Test ServiceInstance stores grpc_port"""
        instance = ServiceInstance(
            service_name="test-service",
            instance_id="test-1",
            host="localhost",
            port=8080,
            grpc_port=50051,
        )
        assert instance.grpc_port == 50051

    def test_service_instance_without_grpc_port(self):
        """Test ServiceInstance without grpc_port (backward compatibility)"""
        instance = ServiceInstance(
            service_name="test-service",
            instance_id="test-1",
            host="localhost",
            port=8080,
        )
        assert instance.grpc_port is None


class TestServiceInstanceResponse:
    """Test ServiceInstanceResponse includes new fields"""

    def test_response_includes_instance_url(self):
        """Test that ServiceInstanceResponse includes instance_url"""
        instance = ServiceInstance(
            service_name="test-service",
            instance_id="test-1",
            host="localhost",
            port=8080,
        )
        response = ServiceInstanceResponse.from_service_instance(instance)
        assert response.instance_url == "http://localhost:8080"

    def test_response_includes_grpc_port(self):
        """Test that ServiceInstanceResponse includes grpc_port"""
        instance = ServiceInstance(
            service_name="test-service",
            instance_id="test-1",
            host="localhost",
            port=8080,
            grpc_port=50051,
        )
        response = ServiceInstanceResponse.from_service_instance(instance)
        assert response.grpc_port == 50051

    def test_response_grpc_port_none(self):
        """Test that ServiceInstanceResponse handles None grpc_port"""
        instance = ServiceInstance(
            service_name="test-service",
            instance_id="test-1",
            host="localhost",
            port=8080,
        )
        response = ServiceInstanceResponse.from_service_instance(instance)
        assert response.grpc_port is None

    def test_response_with_both_fields(self):
        """Test ServiceInstanceResponse with both new fields"""
        instance = ServiceInstance(
            service_name="test-service",
            instance_id="test-1",
            host="localhost",
            port=8080,
            instance_url="https://custom.com:9000",
            grpc_port=50051,
        )
        response = ServiceInstanceResponse.from_service_instance(instance)
        assert response.instance_url == "https://custom.com:9000"
        assert response.grpc_port == 50051


class TestBackwardCompatibility:
    """Test backward compatibility with existing services"""

    def test_registration_without_new_fields(self):
        """Test that registration works without grpc_port and explicit instance_url"""
        request = ServiceRegistrationRequest(
            service_name="legacy-service",
            instance_id="legacy-1",
            host="localhost",
            port=8080,
            health_endpoint="/health",
            metadata={"version": "1.0"},
            topics=["topic1", "topic2"],
        )
        # Should auto-generate instance_url
        assert request.instance_url == "http://localhost:8080"
        # Should have None grpc_port
        assert request.grpc_port is None

    def test_service_instance_backward_compatible(self):
        """Test ServiceInstance creation without new fields"""
        instance = ServiceInstance(
            service_name="legacy-service",
            instance_id="legacy-1",
            host="localhost",
            port=8080,
            health_endpoint="/health",
            metadata={"version": "1.0"},
        )
        assert instance.instance_url == "http://localhost:8080"
        assert instance.grpc_port is None

    def test_minimal_registration_request(self):
        """Test minimal registration request (only required fields)"""
        request = ServiceRegistrationRequest(
            service_name="minimal-service",
            instance_id="minimal-1",
            host="localhost",
            port=8080,
        )
        assert request.service_name == "minimal-service"
        assert request.instance_id == "minimal-1"
        assert request.host == "localhost"
        assert request.port == 8080
        assert request.instance_url == "http://localhost:8080"
        assert request.grpc_port is None
        assert request.health_endpoint == "/health"
        assert request.metadata == {}
        assert request.topics == []


class TestCombinedFields:
    """Test registration with all fields including new ones"""

    def test_full_registration_with_all_fields(self):
        """Test registration with all fields including grpc_port and instance_url"""
        request = ServiceRegistrationRequest(
            service_name="full-service",
            instance_id="full-1",
            host="game-service.local",
            port=8080,
            instance_url="https://game-service.prod.com:8443",
            grpc_port=50051,
            health_endpoint="/api/health",
            metadata={"region": "us-east-1", "version": "2.0"},
            topics=["game.started", "game.ended", "player.joined"],
        )
        assert request.service_name == "full-service"
        assert request.instance_id == "full-1"
        assert request.host == "game-service.local"
        assert request.port == 8080
        assert request.instance_url == "https://game-service.prod.com:8443"
        assert request.grpc_port == 50051
        assert request.health_endpoint == "/api/health"
        assert request.metadata == {"region": "us-east-1", "version": "2.0"}
        assert request.topics == ["game.started", "game.ended", "player.joined"]

    def test_service_instance_with_all_fields(self):
        """Test ServiceInstance with all fields"""
        instance = ServiceInstance(
            service_name="full-service",
            instance_id="full-1",
            host="game-service.local",
            port=8080,
            instance_url="https://game-service.prod.com:8443",
            grpc_port=50051,
            health_endpoint="/api/health",
            metadata={"region": "us-east-1"},
            topics=["game.started", "game.ended"],
        )
        assert instance.service_name == "full-service"
        assert instance.instance_id == "full-1"
        assert instance.host == "game-service.local"
        assert instance.port == 8080
        assert instance.instance_url == "https://game-service.prod.com:8443"
        assert instance.grpc_port == 50051
        assert instance.health_endpoint == "/api/health"
        assert instance.metadata == {"region": "us-east-1"}
        assert instance.topics == ["game.started", "game.ended"]
