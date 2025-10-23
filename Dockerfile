FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy poetry files
COPY pyproject.toml README.md ./

# Install poetry and dependencies
RUN pip install poetry && \
    poetry config virtualenvs.create false && \
    poetry install --only=main --no-root

# Copy application code
COPY service_discovery/ ./service_discovery/

# Expose port
EXPOSE 3004

# Run the application
CMD ["python", "-m", "service_discovery.main"]
