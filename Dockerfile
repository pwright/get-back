FROM golang:1.22-alpine AS go-builder
WORKDIR /build
COPY clients/halfclose_client.go .
RUN go build -o halfclose_client halfclose_client.go

FROM python:3.13

WORKDIR /app



RUN pip install --upgrade pip
RUN apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/*


# Copy application code (exclude cache)
COPY getback/ getback/
COPY clients/ clients/

# Copy compiled Go binary
COPY --from=go-builder /build/halfclose_client /usr/local/bin/halfclose_client



# Remove any cached bytecode that may have been copied
RUN find /app -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
RUN find /app -type f -name "*.pyc" -delete

# Expose HTTP, TCP, and Dashboard ports
EXPOSE 9091 9092 9093

# Run the service
CMD ["python", "-m", "getback"]
