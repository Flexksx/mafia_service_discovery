"""
Tests for Topic Subscription functionality in Service Discovery
"""

import pytest
from fastapi.testclient import TestClient
from service_discovery.main import app
from service_discovery.service_registration.registry import service_registry
from service_discovery.types import ServiceInstance, ServiceStatus
from service_discovery.config import SERVICE_DISCOVERY_SECRET

client = TestClient(app)

# Test headers with authentication
HEADERS = {"Authorization": f"Bearer {SERVICE_DISCOVERY_SECRET}"}


@pytest.fixture(autouse=True)
async def clear_registry():
    """Clear registry before each test"""
    service_registry._services.clear()
    yield
    service_registry._services.clear()


class TestTopicSubscriptions:
    """Test topic subscription functionality"""
    
    def test_register_service_with_topics(self):
        """Test registering a service with topic subscriptions"""
        response = client.post(
            "/v1/discovery/register",
            json={
                "service_name": "billing-service",
                "instance_id": "billing-1",
                "host": "localhost",
                "port": 8080,
                "topics": ["order.created", "payment.failed"]
            },
            headers=HEADERS
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "registered successfully" in data["message"]
    
    def test_register_service_without_topics(self):
        """Test registering a service without topics (backwards compatibility)"""
        response = client.post(
            "/v1/discovery/register",
            json={
                "service_name": "simple-service",
                "instance_id": "simple-1",
                "host": "localhost",
                "port": 8080
            },
            headers=HEADERS
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
    
    def test_get_service_with_topics(self):
        """Test that service details include topics"""
        # Register service
        client.post(
            "/v1/discovery/register",
            json={
                "service_name": "billing-service",
                "instance_id": "billing-1",
                "host": "localhost",
                "port": 8080,
                "topics": ["order.created", "payment.failed"]
            },
            headers=HEADERS
        )
        
        # Get service details
        response = client.get("/v1/discovery/services/billing-service")
        
        assert response.status_code == 200
        data = response.json()
        assert data["service_name"] == "billing-service"
        assert len(data["instances"]) == 1
        
        instance = data["instances"][0]
        assert "topics" in instance
        assert "order.created" in instance["topics"]
        assert "payment.failed" in instance["topics"]
    
    def test_get_all_topic_subscriptions(self):
        """Test GET /services/topics endpoint"""
        # Register multiple services with topics
        client.post(
            "/v1/discovery/register",
            json={
                "service_name": "billing-service",
                "instance_id": "billing-1",
                "host": "localhost",
                "port": 8080,
                "topics": ["order.created", "payment.failed"]
            },
            headers=HEADERS
        )
        
        client.post(
            "/v1/discovery/register",
            json={
                "service_name": "notification-service",
                "instance_id": "notification-1",
                "host": "localhost",
                "port": 8081,
                "topics": ["order.created", "user.registered"]
            },
            headers=HEADERS
        )
        
        # Query topic subscriptions
        response = client.get("/v1/discovery/services/topics")
        
        assert response.status_code == 200
        data = response.json()
        assert "topics" in data
        
        topics = {t["topic"]: t["services"] for t in data["topics"]}
        
        # Check order.created has both services
        assert "order.created" in topics
        assert "billing-service" in topics["order.created"]
        assert "notification-service" in topics["order.created"]
        
        # Check payment.failed has only billing service
        assert "payment.failed" in topics
        assert "billing-service" in topics["payment.failed"]
        assert "notification-service" not in topics["payment.failed"]
        
        # Check user.registered has only notification service
        assert "user.registered" in topics
        assert "notification-service" in topics["user.registered"]
        assert "billing-service" not in topics["user.registered"]
    
    def test_empty_topic_subscriptions(self):
        """Test GET /services/topics when no services are registered"""
        response = client.get("/v1/discovery/services/topics")
        
        assert response.status_code == 200
        data = response.json()
        assert "topics" in data
        assert len(data["topics"]) == 0
    
    def test_multiple_instances_same_service_same_topics(self):
        """Test that multiple instances of same service don't duplicate topics"""
        # Register multiple instances of same service
        for i in range(3):
            client.post(
                "/v1/discovery/register",
                json={
                    "service_name": "billing-service",
                    "instance_id": f"billing-{i}",
                    "host": "localhost",
                    "port": 8080 + i,
                    "topics": ["order.created", "payment.failed"]
                },
                headers=HEADERS
            )
        
        # Query topics
        response = client.get("/v1/discovery/services/topics")
        
        assert response.status_code == 200
        data = response.json()
        topics = {t["topic"]: t["services"] for t in data["topics"]}
        
        # Each topic should have billing-service only once
        assert len(topics["order.created"]) == 1
        assert topics["order.created"][0] == "billing-service"
        assert len(topics["payment.failed"]) == 1
        assert topics["payment.failed"][0] == "billing-service"
    
    def test_service_with_empty_topics_array(self):
        """Test registering service with empty topics array"""
        response = client.post(
            "/v1/discovery/register",
            json={
                "service_name": "simple-service",
                "instance_id": "simple-1",
                "host": "localhost",
                "port": 8080,
                "topics": []
            },
            headers=HEADERS
        )
        
        assert response.status_code == 200
        
        # Topics endpoint should not include this service
        response = client.get("/v1/discovery/services/topics")
        assert response.status_code == 200
        data = response.json()
        assert len(data["topics"]) == 0


class TestServiceRegistryTopicMethods:
    """Test ServiceRegistry topic-related methods"""
    
    @pytest.mark.asyncio
    async def test_get_all_topic_subscriptions(self):
        """Test get_all_topic_subscriptions method"""
        # Register services
        await service_registry.register_service(
            ServiceInstance(
                service_name="billing-service",
                instance_id="billing-1",
                host="localhost",
                port=8080,
                topics=["order.created", "payment.failed"]
            )
        )
        
        await service_registry.register_service(
            ServiceInstance(
                service_name="notification-service",
                instance_id="notification-1",
                host="localhost",
                port=8081,
                topics=["order.created", "user.registered"]
            )
        )
        
        # Get topic subscriptions
        topic_map = await service_registry.get_all_topic_subscriptions()
        
        assert "order.created" in topic_map
        assert "billing-service" in topic_map["order.created"]
        assert "notification-service" in topic_map["order.created"]
        
        assert "payment.failed" in topic_map
        assert "billing-service" in topic_map["payment.failed"]
        
        assert "user.registered" in topic_map
        assert "notification-service" in topic_map["user.registered"]
    
    @pytest.mark.asyncio
    async def test_get_services_by_topic(self):
        """Test get_services_by_topic method"""
        # Register services
        await service_registry.register_service(
            ServiceInstance(
                service_name="billing-service",
                instance_id="billing-1",
                host="localhost",
                port=8080,
                topics=["order.created", "payment.failed"]
            )
        )
        
        await service_registry.register_service(
            ServiceInstance(
                service_name="notification-service",
                instance_id="notification-1",
                host="localhost",
                port=8081,
                topics=["order.created"]
            )
        )
        
        # Query services by topic
        services = await service_registry.get_services_by_topic("order.created")
        assert len(services) == 2
        assert "billing-service" in services
        assert "notification-service" in services
        
        services = await service_registry.get_services_by_topic("payment.failed")
        assert len(services) == 1
        assert "billing-service" in services
        
        services = await service_registry.get_services_by_topic("nonexistent.topic")
        assert len(services) == 0
    
    @pytest.mark.asyncio
    async def test_topic_subscriptions_empty_registry(self):
        """Test topic subscriptions with empty registry"""
        topic_map = await service_registry.get_all_topic_subscriptions()
        assert len(topic_map) == 0
        
        services = await service_registry.get_services_by_topic("any.topic")
        assert len(services) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
