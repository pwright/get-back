FROM python:3.11-slim

WORKDIR /app

# Copy application code
COPY getback/ getback/
COPY clients/ clients/

# Expose HTTP, TCP, and Dashboard ports
EXPOSE 9091 9092 9093

# Run the service
CMD ["python", "-m", "getback"]
