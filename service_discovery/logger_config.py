"""
Logger configuration for Service Discovery
Compatible with Grafana, Loki, and Prometheus monitoring stack
"""

import logging
import logging.config
import sys
from typing import Dict, Any, Optional
import json
from datetime import datetime

from service_discovery.config import LOG_LEVEL, LOG_FORMAT


class StructuredFormatter(logging.Formatter):
    """
    Structured JSON formatter for better integration with Grafana/Loki/Prometheus
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add service discovery specific fields
        if hasattr(record, "service_name"):
            log_entry["service_name"] = getattr(record, "service_name")
        if hasattr(record, "instance_id"):
            log_entry["instance_id"] = getattr(record, "instance_id")
        if hasattr(record, "load_percentage"):
            log_entry["load_percentage"] = getattr(record, "load_percentage")
        if hasattr(record, "status"):
            log_entry["status"] = getattr(record, "status")
        if hasattr(record, "endpoint"):
            log_entry["endpoint"] = getattr(record, "endpoint")
        if hasattr(record, "response_time_ms"):
            log_entry["response_time_ms"] = getattr(record, "response_time_ms")

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in {
                "name",
                "msg",
                "args",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
                "getMessage",
                "exc_info",
                "exc_text",
                "stack_info",
            }:
                log_entry[key] = value

        return json.dumps(log_entry, ensure_ascii=False)


class ServiceDiscoveryLogger:
    """
    Centralized logger configuration for Service Discovery
    """

    @staticmethod
    def setup_logging(
        level: str = LOG_LEVEL,
        format_type: str = "structured",
        enable_console: bool = True,
        enable_file: bool = False,
        log_file_path: Optional[str] = None,
    ) -> None:
        """
        Setup logging configuration

        Args:
            level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            format_type: Format type - "structured" (JSON) or "simple" (text)
            enable_console: Enable console logging
            enable_file: Enable file logging
            log_file_path: Path to log file (required if enable_file=True)
        """

        # Convert string level to logging constant
        numeric_level = getattr(logging, level.upper(), logging.INFO)

        # Choose formatter based on format_type
        if format_type == "structured":
            formatter_class = StructuredFormatter
            format_string = None
        else:
            formatter_class = logging.Formatter
            format_string = LOG_FORMAT

        # Configure handlers
        handlers = []

        if enable_console:
            console_handler = logging.StreamHandler(sys.stdout)
            if format_type == "structured":
                console_handler.setFormatter(formatter_class())
            else:
                console_handler.setFormatter(formatter_class(format_string))
            handlers.append(console_handler)

        if enable_file and log_file_path:
            file_handler = logging.FileHandler(log_file_path)
            if format_type == "structured":
                file_handler.setFormatter(formatter_class())
            else:
                file_handler.setFormatter(formatter_class(format_string))
            handlers.append(file_handler)

        # Configure root logger
        logging.basicConfig(
            level=numeric_level,
            handlers=handlers,
            force=True,  # Override any existing configuration
        )

        # Configure specific loggers
        ServiceDiscoveryLogger._configure_service_loggers(numeric_level, handlers)

    @staticmethod
    def _configure_service_loggers(level: int, handlers: list) -> None:
        """Configure specific service loggers with appropriate levels"""

        # Service discovery main logger
        main_logger = logging.getLogger("service_discovery")
        main_logger.setLevel(level)
        main_logger.handlers = handlers
        main_logger.propagate = False

        # Health monitor logger
        health_logger = logging.getLogger(
            "service_discovery.service_registration.health_monitor"
        )
        health_logger.setLevel(level)
        health_logger.handlers = handlers
        health_logger.propagate = False

        # Registry logger
        registry_logger = logging.getLogger(
            "service_discovery.service_registration.registry"
        )
        registry_logger.setLevel(level)
        registry_logger.handlers = handlers
        registry_logger.propagate = False

        # API logger
        api_logger = logging.getLogger("service_discovery.api")
        api_logger.setLevel(level)
        api_logger.handlers = handlers
        api_logger.propagate = False

        # Client logger
        client_logger = logging.getLogger("service_discovery.client")
        client_logger.setLevel(level)
        client_logger.handlers = handlers
        client_logger.propagate = False

    @staticmethod
    def get_logger(name: str) -> logging.Logger:
        """Get a logger instance"""
        return logging.getLogger(name)

    @staticmethod
    def log_service_event(
        logger: logging.Logger,
        level: int,
        message: str,
        service_name: str,
        instance_id: str,
        **kwargs,
    ) -> None:
        """
        Log a service-related event with structured data

        Args:
            logger: Logger instance
            level: Log level
            message: Log message
            service_name: Name of the service
            instance_id: Instance ID
            **kwargs: Additional structured data
        """
        extra_data = {
            "service_name": service_name,
            "instance_id": instance_id,
            **kwargs,
        }
        logger.log(level, message, extra=extra_data)

    @staticmethod
    def log_health_check(
        logger: logging.Logger,
        level: int,
        message: str,
        service_name: str,
        instance_id: str,
        status: str,
        load_percentage: float,
        response_time_ms: Optional[float] = None,
        endpoint: Optional[str] = None,
        **kwargs,
    ) -> None:
        """
        Log a health check event with structured data

        Args:
            logger: Logger instance
            level: Log level
            message: Log message
            service_name: Name of the service
            instance_id: Instance ID
            status: Health status
            load_percentage: Load percentage
            response_time_ms: Response time in milliseconds
            endpoint: Health check endpoint
            **kwargs: Additional structured data
        """
        extra_data = {
            "service_name": service_name,
            "instance_id": instance_id,
            "status": status,
            "load_percentage": load_percentage,
            **kwargs,
        }

        if response_time_ms is not None:
            extra_data["response_time_ms"] = response_time_ms
        if endpoint is not None:
            extra_data["endpoint"] = endpoint

        logger.log(level, message, extra=extra_data)

    @staticmethod
    def log_critical_alert(
        logger: logging.Logger,
        message: str,
        service_name: str,
        instance_id: str,
        load_percentage: float,
        threshold: float,
        **kwargs,
    ) -> None:
        """
        Log a critical load alert with structured data

        Args:
            logger: Logger instance
            message: Alert message
            service_name: Name of the service
            instance_id: Instance ID
            load_percentage: Current load percentage
            threshold: Load threshold
            **kwargs: Additional structured data
        """
        extra_data = {
            "service_name": service_name,
            "instance_id": instance_id,
            "load_percentage": load_percentage,
            "threshold": threshold,
            "alert_type": "critical_load",
            **kwargs,
        }
        logger.warning(message, extra=extra_data)


# Convenience functions for common logging patterns
def get_service_logger(name: str) -> logging.Logger:
    """Get a service logger instance"""
    return ServiceDiscoveryLogger.get_logger(name)


def log_service_registration(
    logger: logging.Logger, service_name: str, instance_id: str, host: str, port: int
) -> None:
    """Log service registration event"""
    ServiceDiscoveryLogger.log_service_event(
        logger,
        logging.INFO,
        f"Service registered: {service_name}:{instance_id} at {host}:{port}",
        service_name,
        instance_id,
        host=host,
        port=port,
        event_type="registration",
    )


def log_service_unregistration(
    logger: logging.Logger, service_name: str, instance_id: str
) -> None:
    """Log service unregistration event"""
    ServiceDiscoveryLogger.log_service_event(
        logger,
        logging.INFO,
        f"Service unregistered: {service_name}:{instance_id}",
        service_name,
        instance_id,
        event_type="unregistration",
    )


def log_health_check_success(
    logger: logging.Logger,
    service_name: str,
    instance_id: str,
    load_percentage: float,
    response_time_ms: float,
    endpoint: str,
) -> None:
    """Log successful health check"""
    ServiceDiscoveryLogger.log_health_check(
        logger,
        logging.DEBUG,
        f"Health check successful for {service_name}:{instance_id}",
        service_name,
        instance_id,
        status="healthy",
        load_percentage=load_percentage,
        response_time_ms=response_time_ms,
        endpoint=endpoint,
        event_type="health_check_success",
    )


def log_health_check_failure(
    logger: logging.Logger,
    service_name: str,
    instance_id: str,
    error: str,
    endpoint: str,
) -> None:
    """Log failed health check"""
    ServiceDiscoveryLogger.log_health_check(
        logger,
        logging.WARNING,
        f"Health check failed for {service_name}:{instance_id}: {error}",
        service_name,
        instance_id,
        status="unhealthy",
        load_percentage=0.0,
        endpoint=endpoint,
        error=error,
        event_type="health_check_failure",
    )


def log_critical_load_alert(
    logger: logging.Logger,
    service_name: str,
    instance_id: str,
    load_percentage: float,
    threshold: float,
) -> None:
    """Log critical load alert"""
    ServiceDiscoveryLogger.log_critical_alert(
        logger,
        f"CRITICAL LOAD ALERT: Service {service_name}:{instance_id} is at {load_percentage:.1%} load (threshold: {threshold:.1%})",
        service_name,
        instance_id,
        load_percentage,
        threshold,
    )
