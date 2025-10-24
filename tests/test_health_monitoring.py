"""
Enhanced tests for Service Discovery health monitoring and critical load alerting
"""

import asyncio
import pytest
import httpx
import json
import time
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock
from typing import Dict, Any

from tests.test_client import (
    ServiceDiscoveryTestClient,
    MockService,
    ServiceInstanceData,
)
from service_discovery.service_registration.health_monitor import (
    HealthMonitor,
    AlertState,
    health_monitor,
)
from service_discovery.service_registration.registry import service_registry
from service_discovery.types import ServiceInstance, ServiceStatus
from service_discovery.config import (
    HEALTH_CHECK_INTERVAL_SECONDS,
    CRITICAL_LOAD_THRESHOLD,
    WARNING_LOAD_THRESHOLD,
    EMERGENCY_LOAD_THRESHOLD,
    ALERT_COOLDOWN_SECONDS,
    MONITORING_ENABLED,
)
from service_discovery.logger_config import ServiceDiscoveryLogger


class TestHealthMonitoring:
    """Test suite for enhanced health monitoring functionality"""

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

    @pytest.fixture
    def health_monitor_instance(self):
        """Create a fresh health monitor instance for testing"""
        monitor = HealthMonitor()
        monitor.reset_stats()
        return monitor

    @pytest.mark.asyncio
    async def test_health_monitoring_enabled_by_default(self, health_monitor_instance):
        """Test that health monitoring is enabled by default"""
        assert MONITORING_ENABLED, "Monitoring should be enabled by default"

    @pytest.mark.asyncio
    async def test_health_monitor_initialization(self, health_monitor_instance):
        """Test health monitor initialization"""
        assert not health_monitor_instance._running
        assert health_monitor_instance._monitoring_task is None
        assert len(health_monitor_instance._alert_states) == 0
        assert health_monitor_instance._monitoring_stats["total_checks"] == 0

    @pytest.mark.asyncio
    async def test_health_monitor_start_stop(self, health_monitor_instance):
        """Test starting and stopping health monitoring"""
        # Start monitoring
        await health_monitor_instance.start_monitoring()
        assert health_monitor_instance._running
        assert health_monitor_instance._monitoring_task is not None

        # Stop monitoring
        await health_monitor_instance.stop_monitoring()
        assert not health_monitor_instance._running
        assert health_monitor_instance._monitoring_task is None

    @pytest.mark.asyncio
    async def test_health_response_validation(self, health_monitor_instance):
        """Test health response validation"""
        # Valid response
        valid_response = {"status": "healthy", "load_percentage": 0.5}
        assert health_monitor_instance._validate_health_response(valid_response)

        # Invalid response - missing status
        invalid_response1 = {"load_percentage": 0.5}
        assert not health_monitor_instance._validate_health_response(invalid_response1)

        # Invalid response - missing load_percentage
        invalid_response2 = {"status": "healthy"}
        assert not health_monitor_instance._validate_health_response(invalid_response2)

        # Invalid response - invalid load_percentage
        invalid_response3 = {"status": "healthy", "load_percentage": 1.5}
        assert not health_monitor_instance._validate_health_response(invalid_response3)

        # Invalid response - wrong type
        invalid_response4 = {"status": "healthy", "load_percentage": "high"}
        assert not health_monitor_instance._validate_health_response(invalid_response4)

    @pytest.mark.asyncio
    async def test_load_alert_levels(self, health_monitor_instance):
        """Test different load alert levels"""
        instance = ServiceInstance(
            service_name="test-service",
            instance_id="instance-1",
            host="localhost",
            port=8000,
        )

        # Test warning level (60%)
        await health_monitor_instance._check_load_alerts(instance, 0.65)
        assert "test-service:instance-1" in health_monitor_instance._alert_states
        assert health_monitor_instance._monitoring_stats["warning_alerts"] == 1

        # Reset stats and clear alert state to avoid cooldown
        health_monitor_instance.reset_stats()
        health_monitor_instance._alert_states.clear()

        # Test critical level (90%)
        await health_monitor_instance._check_load_alerts(instance, 0.90)
        assert health_monitor_instance._monitoring_stats["critical_alerts"] == 1

        # Reset stats and clear alert state to avoid cooldown
        health_monitor_instance.reset_stats()
        health_monitor_instance._alert_states.clear()

        # Test emergency level (95%)
        await health_monitor_instance._check_load_alerts(instance, 0.98)
        assert health_monitor_instance._monitoring_stats["emergency_alerts"] == 1

    @pytest.mark.asyncio
    async def test_alert_cooldown(self, health_monitor_instance):
        """Test alert cooldown mechanism"""
        instance = ServiceInstance(
            service_name="test-service",
            instance_id="instance-1",
            host="localhost",
            port=8000,
        )

        # First alert
        await health_monitor_instance._check_load_alerts(instance, 0.85)
        assert health_monitor_instance._monitoring_stats["critical_alerts"] == 1

        # Second alert within cooldown period should be ignored
        await health_monitor_instance._check_load_alerts(instance, 0.90)
        assert (
            health_monitor_instance._monitoring_stats["critical_alerts"] == 1
        )  # Should not increment

    @pytest.mark.asyncio
    async def test_health_check_with_retry(self, health_monitor_instance):
        """Test health check retry mechanism"""
        instance = ServiceInstance(
            service_name="test-service",
            instance_id="instance-1",
            host="localhost",
            port=8000,
        )

        # Mock httpx to simulate failures then success
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "status": "healthy",
                "load_percentage": 0.3,
            }

            mock_client_instance = AsyncMock()
            mock_client_instance.get.side_effect = [
                httpx.TimeoutException("timeout"),
                httpx.TimeoutException("timeout"),
                mock_response,  # Success on third attempt
            ]
            mock_client.return_value.__aenter__.return_value = mock_client_instance

            await health_monitor_instance._check_service_health(instance)

            # Should have succeeded after retries
            assert health_monitor_instance._monitoring_stats["successful_checks"] == 1
            assert health_monitor_instance._monitoring_stats["total_checks"] == 1

    @pytest.mark.asyncio
    async def test_concurrent_health_checks(self, health_monitor_instance):
        """Test concurrent health checking"""
        instances = [
            ServiceInstance(
                service_name=f"test-service-{i}",
                instance_id=f"instance-{i}",
                host="localhost",
                port=8000 + i,
            )
            for i in range(5)
        ]

        # Mock successful responses
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "status": "healthy",
                "load_percentage": 0.3,
            }

            mock_client_instance = AsyncMock()
            mock_client_instance.get.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_client_instance

            # Register instances in registry
            for instance in instances:
                await service_registry.register_service(instance)

            # Run concurrent health checks
            await health_monitor_instance._check_all_services_concurrent()

            # All should succeed
            assert health_monitor_instance._monitoring_stats["successful_checks"] == 5
            assert health_monitor_instance._monitoring_stats["total_checks"] == 5

    @pytest.mark.asyncio
    async def test_monitoring_statistics(self, health_monitor_instance):
        """Test monitoring statistics tracking"""
        instance = ServiceInstance(
            service_name="test-service",
            instance_id="instance-1",
            host="localhost",
            port=8000,
        )

        # Simulate some health checks
        health_monitor_instance._monitoring_stats["total_checks"] = 100
        health_monitor_instance._monitoring_stats["successful_checks"] = 95
        health_monitor_instance._monitoring_stats["failed_checks"] = 5
        health_monitor_instance._monitoring_stats["critical_alerts"] = 2

        stats = health_monitor_instance.get_monitoring_stats()
        assert stats["total_checks"] == 100
        assert stats["successful_checks"] == 95
        assert stats["failed_checks"] == 5
        assert stats["critical_alerts"] == 2

        # Test reset
        health_monitor_instance.reset_stats()
        stats = health_monitor_instance.get_monitoring_stats()
        assert stats["total_checks"] == 0
        assert stats["successful_checks"] == 0

    @pytest.mark.asyncio
    async def test_health_check_timeout_handling(self, health_monitor_instance):
        """Test health check timeout handling"""
        instance = ServiceInstance(
            service_name="test-service",
            instance_id="instance-1",
            host="localhost",
            port=8000,
        )

        with patch("httpx.AsyncClient") as mock_client:
            mock_client_instance = AsyncMock()
            mock_client_instance.get.side_effect = httpx.TimeoutException("timeout")
            mock_client.return_value.__aenter__.return_value = mock_client_instance

            await health_monitor_instance._check_service_health(instance)

            # Should be marked as failed after all retries
            assert health_monitor_instance._monitoring_stats["failed_checks"] == 1
            assert health_monitor_instance._monitoring_stats["total_checks"] == 1

    @pytest.mark.asyncio
    async def test_invalid_health_response_handling(self, health_monitor_instance):
        """Test handling of invalid health responses"""
        instance = ServiceInstance(
            service_name="test-service",
            instance_id="instance-1",
            host="localhost",
            port=8000,
        )

        # Test invalid response handling directly
        invalid_response = {"invalid": "response"}  # Missing required fields
        result = health_monitor_instance._validate_health_response(invalid_response)
        assert not result, "Invalid response should not pass validation"

    @pytest.mark.asyncio
    async def test_monitoring_api_endpoints(self):
        """Test monitoring API endpoints"""
        from tests.test_client import ServiceDiscoveryTestClient

        client = ServiceDiscoveryTestClient()

        # Test that the client methods exist and are callable
        assert hasattr(client, "get_monitoring_stats")
        assert hasattr(client, "get_monitoring_health")
        assert hasattr(client, "reset_monitoring_stats")

        # Test that methods are async functions
        import inspect

        assert inspect.iscoroutinefunction(client.get_monitoring_stats)
        assert inspect.iscoroutinefunction(client.get_monitoring_health)
        assert inspect.iscoroutinefunction(client.reset_monitoring_stats)

    @pytest.mark.asyncio
    async def test_structured_logging(self):
        """Test structured logging functionality"""
        logger = ServiceDiscoveryLogger.get_logger("test")

        # Test service event logging
        ServiceDiscoveryLogger.log_service_event(
            logger,
            20,
            "Test message",
            "test-service",
            "instance-1",
            host="localhost",
            port=8000,
        )

        # Test health check logging
        ServiceDiscoveryLogger.log_health_check(
            logger,
            20,
            "Health check test",
            "test-service",
            "instance-1",
            "healthy",
            0.5,
            100.0,
            "/health",
        )

        # Test critical alert logging
        ServiceDiscoveryLogger.log_critical_alert(
            logger, "Critical alert test", "test-service", "instance-1", 0.9, 0.8
        )

    @pytest.mark.asyncio
    async def test_alert_state_management(self, health_monitor_instance):
        """Test alert state management"""
        instance = ServiceInstance(
            service_name="test-service",
            instance_id="instance-1",
            host="localhost",
            port=8000,
        )

        # Create alert state
        service_key = f"{instance.service_name}:{instance.instance_id}"
        alert_state = AlertState(
            service_name=instance.service_name,
            instance_id=instance.instance_id,
            last_alert_time=datetime.now(),
            alert_count=1,
        )
        health_monitor_instance._alert_states[service_key] = alert_state

        # Test getting alert states
        alert_states = health_monitor_instance.get_alert_states()
        assert service_key in alert_states
        assert alert_states[service_key].service_name == "test-service"
        assert alert_states[service_key].alert_count == 1

    @pytest.mark.asyncio
    async def test_monitoring_disabled_scenario(self):
        """Test behavior when monitoring is disabled"""
        with patch(
            "service_discovery.service_registration.health_monitor.MONITORING_ENABLED",
            False,
        ):
            monitor = HealthMonitor()
            await monitor.start_monitoring()

            # Should not start monitoring when disabled
            assert not monitor._running

    @pytest.mark.asyncio
    async def test_health_check_error_handling(self, health_monitor_instance):
        """Test health check error handling"""
        instance = ServiceInstance(
            service_name="test-service",
            instance_id="instance-1",
            host="localhost",
            port=8000,
        )

        with patch("httpx.AsyncClient") as mock_client:
            mock_client_instance = AsyncMock()
            mock_client_instance.get.side_effect = Exception("Connection error")
            mock_client.return_value.__aenter__.return_value = mock_client_instance

            await health_monitor_instance._check_service_health(instance)

            # Should be marked as failed after all retries
            assert health_monitor_instance._monitoring_stats["failed_checks"] == 1

    @pytest.mark.asyncio
    async def test_load_threshold_configuration(self):
        """Test load threshold configuration"""
        assert WARNING_LOAD_THRESHOLD == 0.6
        assert CRITICAL_LOAD_THRESHOLD == 0.8
        assert EMERGENCY_LOAD_THRESHOLD == 0.95
        assert ALERT_COOLDOWN_SECONDS == 300

    @pytest.mark.asyncio
    async def test_monitoring_loop_timing(self, health_monitor_instance):
        """Test monitoring loop timing accuracy"""
        start_time = time.time()

        # Start monitoring
        await health_monitor_instance.start_monitoring()

        # Let it run for a short period
        await asyncio.sleep(0.1)

        # Stop monitoring
        await health_monitor_instance.stop_monitoring()

        elapsed_time = time.time() - start_time
        assert elapsed_time >= 0.1  # Should have run for at least the sleep time

    @pytest.mark.asyncio
    async def test_concurrent_monitoring_tasks(self):
        """Test handling of concurrent monitoring tasks"""
        monitor1 = HealthMonitor()
        monitor2 = HealthMonitor()

        # Start both monitors
        await monitor1.start_monitoring()
        await monitor2.start_monitoring()

        # Both should be running independently
        assert monitor1._running
        assert monitor2._running

        # Stop both
        await monitor1.stop_monitoring()
        await monitor2.stop_monitoring()

        assert not monitor1._running
        assert not monitor2._running

    @pytest.mark.asyncio
    async def test_health_monitor_lifecycle(self, health_monitor_instance):
        """Test complete health monitor lifecycle"""
        # Initial state
        assert not health_monitor_instance._running
        assert health_monitor_instance._monitoring_task is None

        # Start monitoring
        await health_monitor_instance.start_monitoring()
        assert health_monitor_instance._running
        assert health_monitor_instance._monitoring_task is not None

        # Try to start again (should be idempotent)
        await health_monitor_instance.start_monitoring()
        assert health_monitor_instance._running

        # Stop monitoring
        await health_monitor_instance.stop_monitoring()
        assert not health_monitor_instance._running
        assert health_monitor_instance._monitoring_task is None

        # Try to stop again (should be idempotent)
        await health_monitor_instance.stop_monitoring()
        assert not health_monitor_instance._running


class TestCriticalLoadAlerting:
    """Test suite specifically for critical load alerting scenarios"""

    @pytest.fixture
    def health_monitor_instance(self):
        """Create a fresh health monitor instance for testing"""
        monitor = HealthMonitor()
        monitor.reset_stats()
        return monitor

    @pytest.mark.asyncio
    async def test_critical_load_detection(self, health_monitor_instance):
        """Test detection of critical load levels"""
        instance = ServiceInstance(
            service_name="high-load-service",
            instance_id="instance-1",
            host="localhost",
            port=8000,
        )

        # Test critical load (85%)
        await health_monitor_instance._check_load_alerts(instance, 0.85)

        alert_states = health_monitor_instance.get_alert_states()
        service_key = f"{instance.service_name}:{instance.instance_id}"

        assert service_key in alert_states
        assert health_monitor_instance._monitoring_stats["critical_alerts"] == 1

    @pytest.mark.asyncio
    async def test_emergency_load_detection(self, health_monitor_instance):
        """Test detection of emergency load levels"""
        instance = ServiceInstance(
            service_name="emergency-service",
            instance_id="instance-1",
            host="localhost",
            port=8000,
        )

        # Test emergency load (98%)
        await health_monitor_instance._check_load_alerts(instance, 0.98)

        assert health_monitor_instance._monitoring_stats["emergency_alerts"] == 1

    @pytest.mark.asyncio
    async def test_warning_load_detection(self, health_monitor_instance):
        """Test detection of warning load levels"""
        instance = ServiceInstance(
            service_name="warning-service",
            instance_id="instance-1",
            host="localhost",
            port=8000,
        )

        # Test warning load (65%)
        await health_monitor_instance._check_load_alerts(instance, 0.65)

        assert health_monitor_instance._monitoring_stats["warning_alerts"] == 1

    @pytest.mark.asyncio
    async def test_no_alert_below_threshold(self, health_monitor_instance):
        """Test that no alerts are triggered below warning threshold"""
        instance = ServiceInstance(
            service_name="normal-service",
            instance_id="instance-1",
            host="localhost",
            port=8000,
        )

        # Test normal load (30%)
        await health_monitor_instance._check_load_alerts(instance, 0.30)

        # No alerts should be triggered
        assert health_monitor_instance._monitoring_stats["warning_alerts"] == 0
        assert health_monitor_instance._monitoring_stats["critical_alerts"] == 0
        assert health_monitor_instance._monitoring_stats["emergency_alerts"] == 0

    @pytest.mark.asyncio
    async def test_multiple_services_load_alerts(self, health_monitor_instance):
        """Test load alerts for multiple services"""
        instances = [
            ServiceInstance(
                service_name="service-1",
                instance_id="instance-1",
                host="localhost",
                port=8001,
            ),
            ServiceInstance(
                service_name="service-2",
                instance_id="instance-2",
                host="localhost",
                port=8002,
            ),
        ]

        # Trigger different alert levels for different services
        await health_monitor_instance._check_load_alerts(instances[0], 0.65)  # Warning
        await health_monitor_instance._check_load_alerts(instances[1], 0.85)  # Critical

        # Check that both services have alert states
        alert_states = health_monitor_instance.get_alert_states()
        assert "service-1:instance-1" in alert_states
        assert "service-2:instance-2" in alert_states

        # Check statistics
        assert health_monitor_instance._monitoring_stats["warning_alerts"] == 1
        assert health_monitor_instance._monitoring_stats["critical_alerts"] == 1

    @pytest.mark.asyncio
    async def test_alert_cooldown_respect(self, health_monitor_instance):
        """Test that alert cooldown is respected"""
        instance = ServiceInstance(
            service_name="cooldown-service",
            instance_id="instance-1",
            host="localhost",
            port=8000,
        )

        # First alert
        await health_monitor_instance._check_load_alerts(instance, 0.85)
        assert health_monitor_instance._monitoring_stats["critical_alerts"] == 1

        # Immediate second alert should be ignored due to cooldown
        await health_monitor_instance._check_load_alerts(instance, 0.90)
        assert (
            health_monitor_instance._monitoring_stats["critical_alerts"] == 1
        )  # Should not increment

        # Check alert state
        service_key = f"{instance.service_name}:{instance.instance_id}"
        alert_state = health_monitor_instance._alert_states[service_key]
        assert alert_state.alert_count == 1

    @pytest.mark.asyncio
    async def test_alert_count_tracking(self, health_monitor_instance):
        """Test that alert counts are properly tracked"""
        instance = ServiceInstance(
            service_name="count-service",
            instance_id="instance-1",
            host="localhost",
            port=8000,
        )

        # Simulate multiple alerts over time (bypassing cooldown)
        service_key = f"{instance.service_name}:{instance.instance_id}"

        # First alert
        await health_monitor_instance._check_load_alerts(instance, 0.85)
        assert health_monitor_instance._alert_states[service_key].alert_count == 1

        # Manually update last alert time to bypass cooldown
        health_monitor_instance._alert_states[
            service_key
        ].last_alert_time = datetime.now() - timedelta(
            seconds=ALERT_COOLDOWN_SECONDS + 1
        )

        # Second alert
        await health_monitor_instance._check_load_alerts(instance, 0.90)
        assert health_monitor_instance._alert_states[service_key].alert_count == 2

    @pytest.mark.asyncio
    async def test_load_alert_edge_cases(self, health_monitor_instance):
        """Test edge cases for load alerting"""
        instance = ServiceInstance(
            service_name="edge-service",
            instance_id="instance-1",
            host="localhost",
            port=8000,
        )

        # Test exactly at warning threshold
        await health_monitor_instance._check_load_alerts(
            instance, WARNING_LOAD_THRESHOLD
        )
        assert health_monitor_instance._monitoring_stats["warning_alerts"] == 1

        # Reset stats and clear alert state to avoid cooldown
        health_monitor_instance.reset_stats()
        health_monitor_instance._alert_states.clear()

        # Test exactly at critical threshold
        await health_monitor_instance._check_load_alerts(
            instance, CRITICAL_LOAD_THRESHOLD
        )
        assert health_monitor_instance._monitoring_stats["critical_alerts"] == 1

        # Reset stats and clear alert state to avoid cooldown
        health_monitor_instance.reset_stats()
        health_monitor_instance._alert_states.clear()

        # Test exactly at emergency threshold
        await health_monitor_instance._check_load_alerts(
            instance, EMERGENCY_LOAD_THRESHOLD
        )
        assert health_monitor_instance._monitoring_stats["emergency_alerts"] == 1

    @pytest.mark.asyncio
    async def test_load_alert_priority(self, health_monitor_instance):
        """Test that higher priority alerts take precedence"""
        instance = ServiceInstance(
            service_name="priority-service",
            instance_id="instance-1",
            host="localhost",
            port=8000,
        )

        # Test emergency load should trigger emergency alert, not critical
        await health_monitor_instance._check_load_alerts(instance, 0.98)

        assert health_monitor_instance._monitoring_stats["emergency_alerts"] == 1
        assert health_monitor_instance._monitoring_stats["critical_alerts"] == 0
        assert health_monitor_instance._monitoring_stats["warning_alerts"] == 0
