"""
Manual integration test for topic subscriptions
Run this after starting the service with: poetry run uvicorn service_discovery.main:app --reload --port 8001
"""

import requests
import json

BASE_URL = "http://localhost:8001"
SECRET = "test-secret-key"  # Update with your actual secret

def test_topic_subscriptions():
    print("=" * 70)
    print("Testing Topic Subscription Implementation")
    print("=" * 70)
    
    headers = {
        "Authorization": f"Bearer {SECRET}",
        "Content-Type": "application/json"
    }
    
    # Test 1: Register billing service with topics
    print("\n1️⃣  Registering billing-service with topics...")
    response = requests.post(
        f"{BASE_URL}/v1/discovery/register",
        headers=headers,
        json={
            "service_name": "billing-service",
            "instance_id": "billing-1",
            "host": "localhost",
            "port": 8080,
            "topics": ["order.created", "payment.failed", "subscription.updated"]
        }
    )
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}")
    assert response.status_code == 200, "Failed to register billing service"
    assert response.json()["success"] is True
    print("   ✅ Billing service registered successfully")
    
    # Test 2: Register notification service with topics
    print("\n2️⃣  Registering notification-service with topics...")
    response = requests.post(
        f"{BASE_URL}/v1/discovery/register",
        headers=headers,
        json={
            "service_name": "notification-service",
            "instance_id": "notification-1",
            "host": "localhost",
            "port": 8081,
            "topics": ["order.created", "user.registered", "payment.failed"]
        }
    )
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}")
    assert response.status_code == 200
    print("   ✅ Notification service registered successfully")
    
    # Test 3: Register analytics service with topics
    print("\n3️⃣  Registering analytics-service with topics...")
    response = requests.post(
        f"{BASE_URL}/v1/discovery/register",
        headers=headers,
        json={
            "service_name": "analytics-service",
            "instance_id": "analytics-1",
            "host": "localhost",
            "port": 8082,
            "topics": ["order.created", "user.registered"]
        }
    )
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}")
    assert response.status_code == 200
    print("   ✅ Analytics service registered successfully")
    
    # Test 4: Register a service without topics (backwards compatibility)
    print("\n4️⃣  Registering simple-service WITHOUT topics (backwards compatibility)...")
    response = requests.post(
        f"{BASE_URL}/v1/discovery/register",
        headers=headers,
        json={
            "service_name": "simple-service",
            "instance_id": "simple-1",
            "host": "localhost",
            "port": 8083
        }
    )
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}")
    assert response.status_code == 200
    print("   ✅ Simple service registered successfully (no topics)")
    
    # Test 5: Get all services (should include topics)
    print("\n5️⃣  Getting all services (should include topics in response)...")
    response = requests.get(f"{BASE_URL}/v1/discovery/services")
    print(f"   Status: {response.status_code}")
    data = response.json()
    assert response.status_code == 200
    print(f"   Found {len(data['services'])} services")
    
    # Check billing service has topics
    billing_instances = data['services'].get('billing-service', [])
    if billing_instances:
        print(f"   Billing service topics: {billing_instances[0]['topics']}")
        assert "order.created" in billing_instances[0]['topics']
        print("   ✅ Billing service includes topics")
    
    # Test 6: Get topic subscriptions (NEW ENDPOINT)
    print("\n6️⃣  Getting all topic subscriptions (NEW /services/topics endpoint)...")
    response = requests.get(f"{BASE_URL}/v1/discovery/services/topics")
    print(f"   Status: {response.status_code}")
    data = response.json()
    assert response.status_code == 200
    
    print(f"\n   📋 Topic Subscriptions:")
    print(f"   {'-' * 60}")
    
    topics_dict = {t['topic']: t['services'] for t in data['topics']}
    
    for topic_name in sorted(topics_dict.keys()):
        services = topics_dict[topic_name]
        print(f"   • {topic_name}")
        print(f"     Subscribers: {', '.join(services)}")
    
    # Verify expected topics
    assert "order.created" in topics_dict
    assert "payment.failed" in topics_dict
    assert "user.registered" in topics_dict
    assert "subscription.updated" in topics_dict
    
    # Verify order.created has 3 subscribers
    order_created_services = topics_dict["order.created"]
    assert "billing-service" in order_created_services
    assert "notification-service" in order_created_services
    assert "analytics-service" in order_created_services
    print(f"\n   ✅ order.created has {len(order_created_services)} subscribers")
    
    # Verify payment.failed has 2 subscribers
    payment_failed_services = topics_dict["payment.failed"]
    assert "billing-service" in payment_failed_services
    assert "notification-service" in payment_failed_services
    print(f"   ✅ payment.failed has {len(payment_failed_services)} subscribers")
    
    # Verify user.registered has 2 subscribers
    user_registered_services = topics_dict["user.registered"]
    assert "notification-service" in user_registered_services
    assert "analytics-service" in user_registered_services
    print(f"   ✅ user.registered has {len(user_registered_services)} subscribers")
    
    # Verify subscription.updated has 1 subscriber
    subscription_updated_services = topics_dict["subscription.updated"]
    assert "billing-service" in subscription_updated_services
    assert len(subscription_updated_services) == 1
    print(f"   ✅ subscription.updated has {len(subscription_updated_services)} subscriber")
    
    # Test 7: Get specific service (should include topics)
    print("\n7️⃣  Getting billing-service details...")
    response = requests.get(f"{BASE_URL}/v1/discovery/services/billing-service")
    print(f"   Status: {response.status_code}")
    data = response.json()
    assert response.status_code == 200
    assert len(data['instances']) > 0
    topics = data['instances'][0]['topics']
    print(f"   Topics: {topics}")
    assert "order.created" in topics
    assert "payment.failed" in topics
    assert "subscription.updated" in topics
    print("   ✅ Service details include topics")
    
    # Test 8: Clean up - unregister services
    print("\n8️⃣  Cleaning up - unregistering services...")
    services_to_unregister = [
        ("billing-service", "billing-1"),
        ("notification-service", "notification-1"),
        ("analytics-service", "analytics-1"),
        ("simple-service", "simple-1"),
    ]
    
    for service_name, instance_id in services_to_unregister:
        response = requests.delete(
            f"{BASE_URL}/v1/discovery/unregister/{service_name}/{instance_id}",
            headers=headers
        )
        print(f"   Unregistered {service_name}:{instance_id} - Status: {response.status_code}")
    
    # Verify topics endpoint returns empty after cleanup
    print("\n9️⃣  Verifying topic subscriptions are empty after cleanup...")
    response = requests.get(f"{BASE_URL}/v1/discovery/services/topics")
    data = response.json()
    assert len(data['topics']) == 0
    print("   ✅ All topic subscriptions cleaned up")
    
    print("\n" + "=" * 70)
    print("✅ ALL TESTS PASSED!")
    print("=" * 70)
    print("\n📊 Summary:")
    print("   • Service registration with topics: ✅")
    print("   • Backwards compatibility (no topics): ✅")
    print("   • GET /services includes topics: ✅")
    print("   • GET /services/topics endpoint: ✅")
    print("   • Topic-to-services mapping: ✅")
    print("   • Multiple services per topic: ✅")
    print("   • Cleanup and deregistration: ✅")
    print("\n🎉 Topic subscription feature is working perfectly!")


if __name__ == "__main__":
    try:
        test_topic_subscriptions()
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Could not connect to service discovery")
        print("   Please start the service first:")
        print("   poetry run uvicorn service_discovery.main:app --reload --port 8001")
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
