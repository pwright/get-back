"""Command-line interface for Get-Back service."""

import argparse
from .config import Config, load_config


def parse_args() -> Config:
    """Parse command-line arguments and merge with environment config.

    Command-line arguments take precedence over environment variables.

    Returns:
        Config object with values from CLI args (if provided) or environment
    """
    parser = argparse.ArgumentParser(
        description='Get-Back: Dual-Protocol Counter Service',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with defaults (HTTP: 9091, TCP: 9092)
  python -m getback

  # Custom ports
  python -m getback --http-port 8080 --tcp-port 8090

  # Debug logging
  python -m getback --log-level DEBUG

  # Bind to localhost only
  python -m getback --host 127.0.0.1
        """
    )

    # Load defaults from environment
    env_config = load_config()

    parser.add_argument(
        '--http-port',
        type=int,
        default=env_config.http_port,
        help=f'HTTP server port (default: {env_config.http_port}, env: HTTP_PORT)'
    )

    parser.add_argument(
        '--tcp-port',
        type=int,
        default=env_config.tcp_port,
        help=f'TCP server port (default: {env_config.tcp_port}, env: TCP_PORT)'
    )

    parser.add_argument(
        '--dashboard-port',
        type=int,
        default=env_config.dashboard_port,
        help=f'Dashboard server port (default: {env_config.dashboard_port}, env: DASHBOARD_PORT)'
    )

    parser.add_argument(
        '--host',
        type=str,
        default=env_config.host,
        help=f'Bind address (default: {env_config.host}, env: HOST)'
    )

    parser.add_argument(
        '--log-level',
        type=str,
        default=env_config.log_level,
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help=f'Logging level (default: {env_config.log_level}, env: LOG_LEVEL)'
    )

    parser.add_argument(
        '--tls-cert',
        type=str,
        default=env_config.tls_cert_path,
        help=f'Path to TLS certificate file (env: TLS_CERT_PATH)'
    )

    parser.add_argument(
        '--tls-key',
        type=str,
        default=env_config.tls_key_path,
        help=f'Path to TLS private key file (env: TLS_KEY_PATH)'
    )

    args = parser.parse_args()

    return Config(
        http_port=args.http_port,
        tcp_port=args.tcp_port,
        dashboard_port=args.dashboard_port,
        host=args.host,
        log_level=args.log_level,
        server_id=env_config.server_id,
        backend_host=env_config.backend_host,
        tls_cert_path=args.tls_cert,
        tls_key_path=args.tls_key
    )
