import os
from typing import Dict, Optional

# Service Discovery Configuration
SERVICE_DISCOVERY_PORT = int(os.getenv("SERVICE_DISCOVERY_PORT", "3004"))
SERVICE_DISCOVERY_HOST = os.getenv("SERVICE_DISCOVERY_HOST", "0.0.0.0")

# Health Check Configuration
HEALTH_CHECK_INTERVAL_SECONDS = int(os.getenv("HEALTH_CHECK_INTERVAL_SECONDS", "30"))
HEALTH_CHECK_TIMEOUT_SECONDS = int(os.getenv("HEALTH_CHECK_TIMEOUT_SECONDS", "5"))
CRITICAL_LOAD_THRESHOLD = float(os.getenv("CRITICAL_LOAD_THRESHOLD", "0.8"))

# Enhanced Monitoring Configuration
MONITORING_ENABLED = os.getenv("MONITORING_ENABLED", "true").lower() == "true"
HEALTH_CHECK_RETRY_ATTEMPTS = int(os.getenv("HEALTH_CHECK_RETRY_ATTEMPTS", "3"))
HEALTH_CHECK_RETRY_DELAY_SECONDS = int(
    os.getenv("HEALTH_CHECK_RETRY_DELAY_SECONDS", "2")
)
ALERT_COOLDOWN_SECONDS = int(os.getenv("ALERT_COOLDOWN_SECONDS", "300"))  # 5 minutes
MAX_CONCURRENT_HEALTH_CHECKS = int(os.getenv("MAX_CONCURRENT_HEALTH_CHECKS", "10"))

# Load Monitoring Thresholds
WARNING_LOAD_THRESHOLD = float(os.getenv("WARNING_LOAD_THRESHOLD", "0.6"))
CRITICAL_LOAD_THRESHOLD = float(os.getenv("CRITICAL_LOAD_THRESHOLD", "0.8"))
EMERGENCY_LOAD_THRESHOLD = float(os.getenv("EMERGENCY_LOAD_THRESHOLD", "0.95"))

# Health Check Response Validation
EXPECTED_HEALTH_RESPONSE_FIELDS = ["status", "load_percentage"]
HEALTH_CHECK_SUCCESS_STATUS = os.getenv("HEALTH_CHECK_SUCCESS_STATUS", "healthy")

# Service Registration Configuration
SERVICE_REGISTRATION_TTL_SECONDS = int(
    os.getenv("SERVICE_REGISTRATION_TTL_SECONDS", "300")
)  # 5 minutes
SERVICE_HEARTBEAT_INTERVAL_SECONDS = int(
    os.getenv("SERVICE_HEARTBEAT_INTERVAL_SECONDS", "60")
)  # 1 minute

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = os.getenv(
    "LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
LOG_FORMAT_TYPE = os.getenv("LOG_FORMAT_TYPE", "structured")  # "structured" or "simple"
LOG_ENABLE_CONSOLE = os.getenv("LOG_ENABLE_CONSOLE", "true").lower() == "true"
LOG_ENABLE_FILE = os.getenv("LOG_ENABLE_FILE", "false").lower() == "true"
LOG_FILE_PATH = os.getenv("LOG_FILE_PATH", "/var/log/service-discovery.log")

# Service Discovery Secret for internal communication
SERVICE_DISCOVERY_SECRET = os.getenv(
    "SERVICE_DISCOVERY_SECRET", "service-discovery-secret-change-me"
)
