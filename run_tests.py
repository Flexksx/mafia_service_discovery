#!/usr/bin/env python3
"""
Test runner script for Service Discovery

This script handles:
1. Spinning up a docker container (if already up, then put it down and start again)
2. Waiting for it to be ready (with a health endpoint in the service discovery)
3. Running python tests on the service discovery
4. Printing the results
"""

import asyncio
import subprocess
import sys
import time
import logging
import httpx
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class TestRunner:
    """Test runner for service discovery tests"""

    def __init__(self):
        self.project_root = Path(__file__).parent
        self.docker_compose_file = self.project_root / "docker-compose.yml"
        self.service_url = "http://localhost:3004"
        self.max_wait_time = 120  # 2 minutes
        self.docker_compose_cmd = self._detect_docker_compose_command()

    def _detect_docker_compose_command(self) -> list:
        """Detect the correct docker compose command"""
        # Try docker compose (V2) first
        exit_code, _, _ = self.run_command(["docker", "compose", "version"])
        if exit_code == 0:
            logger.info("Using Docker Compose V2 (docker compose)")
            return ["docker", "compose"]

        # Fallback to docker-compose (V1)
        exit_code, _, _ = self.run_command(["docker-compose", "version"])
        if exit_code == 0:
            logger.info("Using Docker Compose V1 (docker-compose)")
            return ["docker-compose"]

        logger.error("Neither 'docker compose' nor 'docker-compose' found!")
        return ["docker", "compose"]  # Default to V2

    def run_command(self, command: list, cwd: Path = None) -> tuple[int, str, str]:
        """Run a shell command and return exit code, stdout, stderr"""
        try:
            result = subprocess.run(
                command,
                cwd=cwd or self.project_root,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            logger.error(f"Command timed out: {' '.join(command)}")
            return 1, "", "Command timed out"
        except Exception as e:
            logger.error(f"Error running command {' '.join(command)}: {e}")
            return 1, "", str(e)

    def stop_docker_services(self):
        """Stop docker services"""
        logger.info("Stopping existing docker services...")
        exit_code, stdout, stderr = self.run_command(
            self.docker_compose_cmd + ["-f", str(self.docker_compose_file), "down"]
        )

        if exit_code != 0:
            logger.warning(f"Failed to stop services: {stderr}")
        else:
            logger.info("Docker services stopped successfully")

    def start_docker_services(self):
        """Start docker services"""
        logger.info("Starting docker services...")
        exit_code, stdout, stderr = self.run_command(
            self.docker_compose_cmd
            + [
                "-f",
                str(self.docker_compose_file),
                "up",
                "-d",
                "--build",
            ]
        )

        if exit_code != 0:
            logger.error(f"Failed to start services: {stderr}")
            return False

        logger.info("Docker services started successfully")
        return True

    async def wait_for_service_ready(self) -> bool:
        """Wait for the service discovery service to be ready"""
        logger.info("Waiting for service discovery to be ready...")

        start_time = time.time()
        while time.time() - start_time < self.max_wait_time:
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    response = await client.get(f"{self.service_url}/health")
                    if response.status_code == 200:
                        logger.info("Service discovery is ready!")
                        return True
            except Exception as e:
                logger.debug(f"Service not ready yet: {e}")

            logger.info("Waiting for service discovery...")
            await asyncio.sleep(5)

        logger.error(f"Service discovery not ready after {self.max_wait_time} seconds")
        return False

    def run_tests(self) -> bool:
        """Run the test suite"""
        logger.info("Running test suite...")

        # Reset port counter before running tests
        try:
            from tests.test_client import reset_port_counter

            reset_port_counter()
            logger.info("Reset port counter for clean test run")
        except Exception as e:
            logger.warning(f"Could not reset port counter: {e}")

        # Install test dependencies if needed
        test_deps = ["pytest", "pytest-asyncio", "httpx"]
        for dep in test_deps:
            exit_code, stdout, stderr = self.run_command(["pip", "install", dep])
            if exit_code != 0:
                logger.warning(f"Failed to install {dep}: {stderr}")

        # Run pytest
        exit_code, stdout, stderr = self.run_command(
            [
                "python",
                "-m",
                "pytest",
                "tests/",
                "-v",
                "--tb=short",
                "--asyncio-mode=auto",
            ]
        )

        logger.info("Test Results:")
        logger.info("=" * 50)
        if stdout:
            logger.info(stdout)
        if stderr:
            logger.error(stderr)

        success = exit_code == 0
        if success:
            logger.info("✅ All tests passed!")
        else:
            logger.error("❌ Some tests failed!")

        return success

    def print_docker_logs(self):
        """Print docker service logs"""
        logger.info("Docker service logs:")
        logger.info("=" * 50)

        exit_code, stdout, stderr = self.run_command(
            self.docker_compose_cmd
            + ["-f", str(self.docker_compose_file), "logs", "--tail=50"]
        )

        if stdout:
            logger.info(stdout)
        if stderr:
            logger.error(stderr)

    async def run(self):
        """Run the complete test suite"""
        logger.info("🚀 Starting Service Discovery Test Suite")
        logger.info("=" * 60)

        try:
            # Step 1: Stop existing services
            self.stop_docker_services()

            # Step 2: Start docker services
            if not self.start_docker_services():
                logger.error("Failed to start docker services")
                return False

            # Step 3: Wait for service to be ready
            if not await self.wait_for_service_ready():
                logger.error("Service discovery service is not ready")
                self.print_docker_logs()
                return False

            # Step 4: Run tests
            test_success = self.run_tests()

            # Print logs if tests failed
            if not test_success:
                self.print_docker_logs()

            return test_success

        except KeyboardInterrupt:
            logger.info("Test run interrupted by user")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during test run: {e}")
            self.print_docker_logs()
            return False
        finally:
            # Always stop services at the end
            logger.info("Cleaning up...")
            self.stop_docker_services()


async def main():
    """Main entry point"""
    runner = TestRunner()
    success = await runner.run()

    if success:
        logger.info("🎉 Test suite completed successfully!")
        sys.exit(0)
    else:
        logger.error("💥 Test suite failed!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
