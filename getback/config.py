"""Configuration management for Get-Back service."""

import os
import socket
from dataclasses import dataclass


def get_server_id() -> str:
    """Get server identity for display in responses.

    Uses HOSTNAME environment variable if available (Kubernetes pod name),
    otherwise falls back to socket.gethostname().

    Returns:
        Server identifier string (e.g., "getback-7d4f8c6b9-abc12" or "laptop.local")
    """
    return os.environ.get("HOSTNAME", socket.gethostname())


@dataclass
class Config:
    """Application configuration.

    Attributes:
        http_port: Port for HTTP server (default: 9091)
        tcp_port: Port for TCP server (default: 9092)
        dashboard_port: Port for dashboard server (default: 9093)
        host: Bind address (default: 0.0.0.0)
        log_level: Logging level (default: INFO)
        server_id: Server identifier for responses
        backend_host: Backend host for dashboard requests (default: localhost)
    """
    http_port: int = 9091
    tcp_port: int = 9092
    dashboard_port: int = 9093
    host: str = "0.0.0.0"
    log_level: str = "INFO"
    server_id: str = ""
    backend_host: str = "localhost"


def load_config() -> Config:
    """Load configuration from environment variables.

    Environment variables:
        HTTP_PORT: HTTP server port
        TCP_PORT: TCP server port
        DASHBOARD_PORT: Dashboard server port
        HOST: Bind address
        LOG_LEVEL: Logging level (DEBUG, INFO, WARNING, ERROR)
        HOSTNAME: Server identifier (Kubernetes pod name)
        BACKEND_HOST: Backend host for dashboard requests (default: localhost)

    Returns:
        Config object with values from environment or defaults
    """
    return Config(
        http_port=int(os.getenv('HTTP_PORT', '9091')),
        tcp_port=int(os.getenv('TCP_PORT', '9092')),
        dashboard_port=int(os.getenv('DASHBOARD_PORT', '9093')),
        host=os.getenv('HOST', '0.0.0.0'),
        log_level=os.getenv('LOG_LEVEL', 'INFO'),
        server_id=get_server_id(),
        backend_host=os.getenv('BACKEND_HOST', 'localhost')
    )
