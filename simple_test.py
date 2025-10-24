#!/usr/bin/env python3
"""
Simple example test for Service Discovery

This is a standalone test that can be run to verify the service discovery
is working correctly. It doesn't require pytest and can be run directly.
"""

import asyncio
import httpx
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_service_discovery():
    """Simple test of service discovery functionality"""

    base_url = "http://localhost:3004"
    secret = "test-secret-key"
    headers = {
        "Authorization": f"Bearer {secret}",
        "Content-Type": "application/json",
    }

    logger.info("🧪 Starting simple service discovery test")

    # Test 1: Health check
    logger.info("Test 1: Health check")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{base_url}/health")
            if response.status_code == 200:
                logger.info("✅ Service discovery is healthy")
            else:
                logger.error(f"❌ Health check failed: {response.status_code}")
                return False
    except Exception as e:
        logger.error(f"❌ Health check failed: {e}")
        return False

    # Test 2: Register a test service
    logger.info("Test 2: Register test service")
    test_service = {
        "service_name": "example-service",
        "instance_id": "instance-1",
        "host": "localhost",
        "port": 8080,
        "health_endpoint": "/health",
        "metadata": {"environment": "test", "version": "1.0.0"},
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/v1/discovery/register", json=test_service, headers=headers
            )
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    logger.info("✅ Service registered successfully")
                else:
                    logger.error(
                        f"❌ Service registration failed: {result.get('message')}"
                    )
                    return False
            else:
                logger.error(f"❌ Registration request failed: {response.status_code}")
                return False
    except Exception as e:
        logger.error(f"❌ Service registration failed: {e}")
        return False

    # Test 3: List services
    logger.info("Test 3: List registered services")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{base_url}/v1/discovery/services")
            if response.status_code == 200:
                data = response.json()
                services = data.get("services", {})
                if "example-service" in services:
                    logger.info("✅ Service found in service list")
                    logger.info(
                        f"   Found {len(services['example-service'])} instance(s)"
                    )
                else:
                    logger.error("❌ Service not found in service list")
                    return False
            else:
                logger.error(f"❌ List services failed: {response.status_code}")
                return False
    except Exception as e:
        logger.error(f"❌ List services failed: {e}")
        return False

    # Test 4: Send heartbeat
    logger.info("Test 4: Send heartbeat")
    heartbeat_data = {"service_name": "example-service", "instance_id": "instance-1"}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/v1/discovery/heartbeat",
                json=heartbeat_data,
                headers=headers,
            )
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    logger.info("✅ Heartbeat sent successfully")
                else:
                    logger.error(f"❌ Heartbeat failed: {result.get('message')}")
                    return False
            else:
                logger.error(f"❌ Heartbeat request failed: {response.status_code}")
                return False
    except Exception as e:
        logger.error(f"❌ Heartbeat failed: {e}")
        return False

    # Test 5: Unregister service
    logger.info("Test 5: Unregister service")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{base_url}/v1/discovery/unregister/example-service/instance-1",
                headers=headers,
            )
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    logger.info("✅ Service unregistered successfully")
                else:
                    logger.error(
                        f"❌ Service unregistration failed: {result.get('message')}"
                    )
                    return False
            else:
                logger.error(
                    f"❌ Unregistration request failed: {response.status_code}"
                )
                return False
    except Exception as e:
        logger.error(f"❌ Service unregistration failed: {e}")
        return False

    # Test 6: Verify service is removed
    logger.info("Test 6: Verify service is removed")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{base_url}/v1/discovery/services")
            if response.status_code == 200:
                data = response.json()
                services = data.get("services", {})
                if (
                    "example-service" not in services
                    or len(services.get("example-service", [])) == 0
                ):
                    logger.info("✅ Service successfully removed")
                else:
                    logger.error("❌ Service still exists after unregistration")
                    return False
            else:
                logger.error(f"❌ Verification failed: {response.status_code}")
                return False
    except Exception as e:
        logger.error(f"❌ Verification failed: {e}")
        return False

    logger.info("🎉 All tests passed!")
    return True


async def main():
    """Main entry point"""
    logger.info("Starting simple service discovery test...")
    logger.info("Make sure the service discovery service is running on localhost:3004")
    logger.info("=" * 60)

    success = await test_service_discovery()

    if success:
        logger.info("✅ Simple test completed successfully!")
    else:
        logger.error("❌ Simple test failed!")
        exit(1)


if __name__ == "__main__":
    asyncio.run(main())
