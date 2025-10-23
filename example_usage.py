#!/usr/bin/env python3
"""
Example script showing how to use the Service Discovery Client

This script demonstrates:
1. Registering a service with the service discovery
2. Sending heartbeats
3. Discovering other services
4. Graceful shutdown with unregistration
"""

import asyncio
import logging
import signal
import sys
from service_discovery.client import (
    ServiceDiscoveryClient,
    register_service_with_discovery,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ExampleService:
    """Example service that registers with service discovery"""

    def __init__(self, service_name: str, instance_id: str, port: int):
        self.service_name = service_name
        self.instance_id = instance_id
        self.port = port
        self.discovery_client: ServiceDiscoveryClient = None
        self.running = False

    async def start(self):
        """Start the example service"""
        logger.info(
            f"Starting {self.service_name}:{self.instance_id} on port {self.port}"
        )

        try:
            # Register with service discovery
            self.discovery_client = await register_service_with_discovery(
                service_name=self.service_name,
                instance_id=self.instance_id,
                host="localhost",  # In real deployment, this would be the actual host
                port=self.port,
                health_endpoint="/health",
                metadata={"version": "1.0.0", "environment": "development"},
                heartbeat_interval=30,  # Send heartbeat every 30 seconds
            )

            self.running = True
            logger.info("Service registered successfully with service discovery")

            # Simulate service work
            await self._service_loop()

        except Exception as e:
            logger.error(f"Failed to start service: {e}")
            await self.stop()

    async def _service_loop(self):
        """Simulate service work"""
        while self.running:
            try:
                # Discover other services
                await self._discover_services()

                # Wait before next discovery
                await asyncio.sleep(60)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in service loop: {e}")
                await asyncio.sleep(5)

    async def _discover_services(self):
        """Discover and log other services"""
        try:
            all_services = await self.discovery_client.list_all_services()

            logger.info("=== Service Discovery Report ===")
            for service_name, instances in all_services.items():
                logger.info(f"Service: {service_name}")
                for instance in instances:
                    logger.info(
                        f"  - {instance.instance_id} at {instance.host}:{instance.port} "
                        f"(status: {instance.status}, load: {instance.load_percentage:.1%})"
                    )

            # Get healthy instances of a specific service
            healthy_instances = await self.discovery_client.discover_services(
                "user-management-service", healthy_only=True
            )
            if healthy_instances:
                logger.info(
                    f"Found {len(healthy_instances)} healthy user-management-service instances"
                )

        except Exception as e:
            logger.error(f"Error discovering services: {e}")

    async def stop(self):
        """Stop the service gracefully"""
        logger.info("Stopping service...")
        self.running = False

        if self.discovery_client:
            # Stop heartbeat loop
            await self.discovery_client.stop_heartbeat_loop()

            # Unregister from service discovery
            await self.discovery_client.unregister_service()

        logger.info("Service stopped")


async def main():
    """Main function"""
    # Create example service
    service = ExampleService(
        service_name="example-service", instance_id="instance-1", port=8080
    )

    # Set up signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        asyncio.create_task(service.stop())

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Start the service
        await service.start()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Service failed: {e}")
    finally:
        await service.stop()


if __name__ == "__main__":
    # Run the example
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Example stopped by user")
    except Exception as e:
        logger.error(f"Example failed: {e}")
        sys.exit(1)
