FROM python:3.13

WORKDIR /app

# Copy application code (exclude cache)
COPY getback/ getback/
COPY clients/ clients/

# Remove any cached bytecode that may have been copied
RUN find /app -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
RUN find /app -type f -name "*.pyc" -delete

# Expose HTTP, TCP, and Dashboard ports
EXPOSE 9091 9092 9093

# Run the service
CMD ["python", "-m", "getback"]
