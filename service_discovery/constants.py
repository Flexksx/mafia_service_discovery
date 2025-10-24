# Service Discovery Constants
# All magic numbers and strings are defined here for maintainability

# HTTP Status Codes
HTTP_OK = 200
HTTP_UNAUTHORIZED = 401
HTTP_NOT_FOUND = 404
HTTP_INTERNAL_SERVER_ERROR = 500

# HTTP Headers
AUTHORIZATION_HEADER = "Authorization"
CONTENT_TYPE_HEADER = "Content-Type"
BEARER_PREFIX = "Bearer "

# API Endpoints
HEALTH_ENDPOINT = "/health"
REGISTER_ENDPOINT = "/register"
HEARTBEAT_ENDPOINT = "/heartbeat"
SERVICES_ENDPOINT = "/services"
UNREGISTER_ENDPOINT = "/unregister"

# Service Status Values
STATUS_HEALTHY = "healthy"
STATUS_UNHEALTHY = "unhealthy"
STATUS_UNKNOWN = "unknown"

# Default Values
DEFAULT_HEALTH_ENDPOINT = "/health"
DEFAULT_HEARTBEAT_INTERVAL = 60
DEFAULT_HEALTH_CHECK_INTERVAL = 30
DEFAULT_HEALTH_CHECK_TIMEOUT = 5
DEFAULT_SERVICE_TTL = 300
DEFAULT_CRITICAL_LOAD_THRESHOLD = 0.8

# Load Calculation Weights
CPU_WEIGHT = 0.5
MEMORY_WEIGHT = 0.3
DISK_WEIGHT = 0.2
MAX_LOAD_PERCENTAGE = 1.0

# Error Messages
ERROR_MISSING_AUTH_HEADER = "Missing Authorization header"
ERROR_INVALID_AUTH_FORMAT = "Invalid Authorization header format"
ERROR_INVALID_SECRET = "Invalid service discovery secret"
ERROR_SERVICE_NOT_FOUND = "Service not found"
ERROR_REGISTRATION_FAILED = "Registration failed"
ERROR_HEARTBEAT_FAILED = "Heartbeat update failed"
ERROR_UNREGISTRATION_FAILED = "Unregistration failed"

# Success Messages
SUCCESS_REGISTERED = "registered successfully"
SUCCESS_HEARTBEAT_UPDATED = "Heartbeat updated successfully"
SUCCESS_UNREGISTERED = "Service unregistered successfully"

# Log Messages
LOG_SERVICE_REGISTERED = "Service registered: {}:{} at {}:{}"
LOG_SERVICE_UNREGISTERED = "Unregistered service: {}:{}"
LOG_HEALTH_MONITORING_STARTED = "Health monitoring started"
LOG_HEALTH_MONITORING_STOPPED = "Health monitoring stopped"
LOG_HEARTBEAT_LOOP_STARTED = "Started heartbeat loop with {}s interval"
LOG_HEARTBEAT_LOOP_STOPPED = "Stopped heartbeat loop"
LOG_EXPIRED_SERVICE_REMOVED = "Removed expired service: {}:{}"
LOG_CRITICAL_LOAD_ALERT = (
    "CRITICAL LOAD ALERT: Service {}:{} is at {:.1%} load (threshold: {:.1%})"
)

# Retry Configuration
RETRY_DELAY_SECONDS = 5
HEARTBEAT_RETRY_DELAY = 5
