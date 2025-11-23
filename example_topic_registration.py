"""
Example: How to register a service with topic subscriptions

This example shows how services should register with Service Discovery
and specify which topics they want to consume.
"""

import asyncio
from service_discovery.client import ServiceDiscoveryClient


async def register_billing_service():
    """Example: Billing service registration with topic subscriptions"""
    
    client = ServiceDiscoveryClient(
        service_discovery_url="http://localhost:8001",
        service_discovery_secret="your-secret-key"
    )
    
    # Register billing service with topics it's interested in
    success = await client.register_service(
        service_name="billing-service",
        instance_id="billing-1",
        host="localhost",
        port=8080,
        health_endpoint="/health",
        metadata={
            "version": "1.0.0",
            "environment": "production"
        },
        topics=[
            "order.created",         # Process new orders
            "order.cancelled",       # Handle cancellations
            "payment.failed",        # Retry failed payments
            "subscription.updated"   # Update billing info
        ]
    )
    
    if success:
        print("✅ Billing service registered with topics")
        
        # Start heartbeat loop
        await client.start_heartbeat_loop(interval_seconds=30)
    else:
        print("❌ Failed to register service")


async def register_notification_service():
    """Example: Notification service registration with topic subscriptions"""
    
    client = ServiceDiscoveryClient(
        service_discovery_url="http://localhost:8001",
        service_discovery_secret="your-secret-key"
    )
    
    # Register notification service with topics it's interested in
    success = await client.register_service(
        service_name="notification-service",
        instance_id="notification-1",
        host="localhost",
        port=8081,
        health_endpoint="/health",
        topics=[
            "user.registered",       # Send welcome email
            "order.created",         # Order confirmation email
            "payment.processed",     # Payment receipt email
            "payment.failed",        # Payment failure alert
            "subscription.cancelled" # Cancellation email
        ]
    )
    
    if success:
        print("✅ Notification service registered with topics")
        await client.start_heartbeat_loop(interval_seconds=30)
    else:
        print("❌ Failed to register service")


async def register_analytics_service():
    """Example: Analytics service registration with topic subscriptions"""
    
    client = ServiceDiscoveryClient(
        service_discovery_url="http://localhost:8001",
        service_discovery_secret="your-secret-key"
    )
    
    # Register analytics service with topics it's interested in
    success = await client.register_service(
        service_name="analytics-service",
        instance_id="analytics-1",
        host="localhost",
        port=8082,
        health_endpoint="/health",
        topics=[
            "user.registered",       # Track user signups
            "order.created",         # Track order metrics
            "payment.processed",     # Revenue tracking
            "subscription.started",  # Subscription metrics
            "subscription.cancelled" # Churn tracking
        ]
    )
    
    if success:
        print("✅ Analytics service registered with topics")
        await client.start_heartbeat_loop(interval_seconds=30)
    else:
        print("❌ Failed to register service")


async def register_service_without_topics():
    """Example: Service registration without topics (backwards compatible)"""
    
    client = ServiceDiscoveryClient(
        service_discovery_url="http://localhost:8001",
        service_discovery_secret="your-secret-key"
    )
    
    # Register service without topics (still works for services that don't use events)
    success = await client.register_service(
        service_name="simple-service",
        instance_id="simple-1",
        host="localhost",
        port=8083,
        health_endpoint="/health"
        # No topics parameter - defaults to empty list
    )
    
    if success:
        print("✅ Simple service registered without topics")
        await client.start_heartbeat_loop(interval_seconds=30)
    else:
        print("❌ Failed to register service")


async def query_topic_subscriptions():
    """Example: How Message Broker queries topic subscriptions"""
    
    import httpx
    
    # Message Broker calls this endpoint to get topic mappings
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:8001/services/topics")
        
        if response.status_code == 200:
            data = response.json()
            print("\n📋 Topic Subscriptions:")
            for topic_info in data["topics"]:
                topic = topic_info["topic"]
                services = topic_info["services"]
                print(f"  • {topic}")
                print(f"    Subscribers: {', '.join(services)}")
        else:
            print(f"❌ Failed to query topics: {response.status_code}")


# Topic Naming Convention
"""
Recommended topic naming: <resource>.<action>

Examples:
- user.registered
- user.updated
- user.deleted
- order.created
- order.updated
- order.cancelled
- payment.processed
- payment.failed
- payment.refunded
- subscription.started
- subscription.updated
- subscription.cancelled
- inventory.low
- inventory.out_of_stock
"""


if __name__ == "__main__":
    # Example: Register services with topics
    print("Example: Service Registration with Topics\n")
    
    # Run one of the examples:
    asyncio.run(register_billing_service())
    
    # Or register multiple services:
    # await asyncio.gather(
    #     register_billing_service(),
    #     register_notification_service(),
    #     register_analytics_service(),
    # )
    
    # Message Broker can query subscriptions:
    # await query_topic_subscriptions()
