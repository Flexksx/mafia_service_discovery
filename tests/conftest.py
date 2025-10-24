# Test configuration
import os

# Test environment variables
os.environ.setdefault("SERVICE_DISCOVERY_URL", "http://localhost:3004")
os.environ.setdefault("SERVICE_DISCOVERY_SECRET", "test-secret-key")
os.environ.setdefault("LOG_LEVEL", "INFO")
