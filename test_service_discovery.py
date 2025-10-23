#!/usr/bin/env python3
"""
Simple test script for the Service Discovery service

This script tests:
1. Service registration
2. Heartbeat functionality
3. Service discovery
4. Health monitoring simulation
"""

import asyncio
import httpx
import logging
import json
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

SERVICE_DISCOVERY_URL = "http://localhost:3004"
SERVICE_DISCOVERY_SECRET = "service-discovery-secret-change-me"


async def test_service_registration():
    """Test service registration"""
    logger.info("Testing service registration...")

    registration_data = {
        "service_name": "test-service",
        "instance_id": "test-instance-1",
        "host": "localhost",
        "port": 8080,
        "health_endpoint": "/health",
        "metadata": {"version": "1.0.0", "test": "true"},
    }

    headers = {
        "Authorization": f"Bearer {SERVICE_DISCOVERY_SECRET}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{SERVICE_DISCOVERY_URL}/v1/discovery/register",
            json=registration_data,
            headers=headers,
        )

        if response.status_code == 200:
            result = response.json()
            logger.info(f"Registration successful: {result}")
            return True
        else:
            logger.error(
                f"Registration failed: {response.status_code} - {response.text}"
            )
            return False


async def test_heartbeat():
    """Test heartbeat functionality"""
    logger.info("Testing heartbeat...")

    heartbeat_data = {"service_name": "test-service", "instance_id": "test-instance-1"}

    headers = {
        "Authorization": f"Bearer {SERVICE_DISCOVERY_SECRET}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{SERVICE_DISCOVERY_URL}/v1/discovery/heartbeat",
            json=heartbeat_data,
            headers=headers,
        )

        if response.status_code == 200:
            result = response.json()
            logger.info(f"Heartbeat successful: {result}")
            return True
        else:
            logger.error(f"Heartbeat failed: {response.status_code} - {response.text}")
            return False


async def test_service_discovery():
    """Test service discovery"""
    logger.info("Testing service discovery...")

    async with httpx.AsyncClient() as client:
        # Test listing all services
        response = await client.get(f"{SERVICE_DISCOVERY_URL}/v1/discovery/services")

        if response.status_code == 200:
            result = response.json()
            logger.info(f"All services: {json.dumps(result, indent=2, default=str)}")
        else:
            logger.error(
                f"Failed to list services: {response.status_code} - {response.text}"
            )

        # Test getting specific service
        response = await client.get(
            f"{SERVICE_DISCOVERY_URL}/v1/discovery/services/test-service"
        )

        if response.status_code == 200:
            result = response.json()
            logger.info(
                f"Test service instances: {json.dumps(result, indent=2, default=str)}"
            )
        else:
            logger.error(
                f"Failed to get test service: {response.status_code} - {response.text}"
            )

        # Test getting healthy instances
        response = await client.get(
            f"{SERVICE_DISCOVERY_URL}/v1/discovery/services/test-service/healthy"
        )

        if response.status_code == 200:
            result = response.json()
            logger.info(
                f"Healthy test service instances: {json.dumps(result, indent=2, default=str)}"
            )
        else:
            logger.error(
                f"Failed to get healthy test service: {response.status_code} - {response.text}"
            )


async def test_health_endpoint():
    """Test the service discovery health endpoint"""
    logger.info("Testing service discovery health endpoint...")

    async with httpx.AsyncClient() as client:
        response = await client.get(f"{SERVICE_DISCOVERY_URL}/health")

        if response.status_code == 200:
            result = response.json()
            logger.info(f"Service discovery health: {result}")
            return True
        else:
            logger.error(
                f"Health check failed: {response.status_code} - {response.text}"
            )
            return False


async def test_unregistration():
    """Test service unregistration"""
    logger.info("Testing service unregistration...")

    headers = {"Authorization": f"Bearer {SERVICE_DISCOVERY_SECRET}"}

    async with httpx.AsyncClient() as client:
        response = await client.delete(
            f"{SERVICE_DISCOVERY_URL}/v1/discovery/unregister/test-service/test-instance-1",
            headers=headers,
        )

        if response.status_code == 200:
            result = response.json()
            logger.info(f"Unregistration successful: {result}")
            return True
        else:
            logger.error(
                f"Unregistration failed: {response.status_code} - {response.text}"
            )
            return False


async def run_tests():
    """Run all tests"""
    logger.info("Starting Service Discovery tests...")

    try:
        # Test health endpoint first
        if not await test_health_endpoint():
            logger.error("Service discovery is not healthy, aborting tests")
            return

        # Test registration
        if not await test_service_registration():
            logger.error("Service registration test failed")
            return

        # Wait a bit
        await asyncio.sleep(2)

        # Test heartbeat
        if not await test_heartbeat():
            logger.error("Heartbeat test failed")
            return

        # Wait a bit
        await asyncio.sleep(2)

        # Test service discovery
        await test_service_discovery()

        # Wait a bit
        await asyncio.sleep(2)

        # Test unregistration
        if not await test_unregistration():
            logger.error("Unregistration test failed")
            return

        logger.info("All tests completed successfully!")

    except Exception as e:
        logger.error(f"Test failed with error: {e}")


if __name__ == "__main__":
    asyncio.run(run_tests())
