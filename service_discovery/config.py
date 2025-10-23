import os
from typing import Dict, Optional

# Service Discovery Configuration
SERVICE_DISCOVERY_PORT = int(os.getenv("SERVICE_DISCOVERY_PORT", "3004"))
SERVICE_DISCOVERY_HOST = os.getenv("SERVICE_DISCOVERY_HOST", "0.0.0.0")

# Health Check Configuration
HEALTH_CHECK_INTERVAL_SECONDS = int(os.getenv("HEALTH_CHECK_INTERVAL_SECONDS", "30"))
HEALTH_CHECK_TIMEOUT_SECONDS = int(os.getenv("HEALTH_CHECK_TIMEOUT_SECONDS", "5"))
CRITICAL_LOAD_THRESHOLD = float(os.getenv("CRITICAL_LOAD_THRESHOLD", "0.8"))

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

# Service Discovery Secret for internal communication
SERVICE_DISCOVERY_SECRET = os.getenv(
    "SERVICE_DISCOVERY_SECRET", "service-discovery-secret-change-me"
)
