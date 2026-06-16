"""Main entry point for Get-Back service."""

import asyncio
import signal
import ssl
import time
from typing import Optional
from . import setup_logging
from .cli import parse_args
from .counter import Counter
from .http_server import start_http_server
from .tcp_server import start_tcp_server
from .dashboard_server import start_dashboard_server


def create_server_ssl_context(cert_path: str, key_path: str) -> Optional[ssl.SSLContext]:
    """Create SSL context for server-side TLS.

    Args:
        cert_path: Path to TLS certificate file
        key_path: Path to TLS private key file

    Returns:
        SSLContext configured for server-side TLS, or None if paths are empty
    """
    if not cert_path or not key_path:
        return None

    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(cert_path, key_path)
    return context


async def main():
    """Start both HTTP and TCP servers concurrently."""
    # Parse configuration
    config = parse_args()

    # Setup logging
    logger = setup_logging(config.log_level)

    # Create SSL context if TLS is configured
    ssl_context = create_server_ssl_context(config.tls_cert_path, config.tls_key_path)
    tls_status = "TLS enabled" if ssl_context else "plain"

    logger.info(f"Starting Get-Back ({tls_status}) | HTTP:{config.http_port} TCP:{config.tcp_port} Dashboard:{config.dashboard_port}")

    # Create independent counters for each protocol
    http_counter = Counter()
    tcp_counter = Counter()
    active_connections = set()
    start_time = time.time()

    # Graceful shutdown handler
    shutdown_event = asyncio.Event()
    shutdown_count = 0

    def handle_shutdown(sig, frame):
        nonlocal shutdown_count
        shutdown_count += 1

        if shutdown_count == 1:
            logger.info(f"\nReceived signal {sig}, shutting down gracefully... (Ctrl+C again to force)")
            shutdown_event.set()
        else:
            logger.warning("\nForce shutdown - exiting immediately")
            import sys
            sys.exit(1)

    # Register signal handlers
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    try:
        # Start all three servers concurrently
        http_task = asyncio.create_task(
            start_http_server(config.host, config.http_port, http_counter, config.server_id, ssl_context)
        )
        tcp_task = asyncio.create_task(
            start_tcp_server(config.host, config.tcp_port, tcp_counter, active_connections, config.server_id, ssl_context)
        )
        dashboard_task = asyncio.create_task(
            start_dashboard_server(config.host, config.dashboard_port, http_counter, tcp_counter, start_time, config.backend_host, ssl_context)
        )

        # Wait for shutdown signal
        await shutdown_event.wait()

        # Cancel server tasks
        http_task.cancel()
        tcp_task.cancel()
        dashboard_task.cancel()

        # Wait for tasks to finish cancellation (with timeout)
        try:
            await asyncio.wait_for(
                asyncio.gather(http_task, tcp_task, dashboard_task, return_exceptions=True),
                timeout=1.0
            )
        except asyncio.TimeoutError:
            logger.warning("Task cancellation timeout - forcing shutdown")

        # Close all active persistent connections in parallel
        if active_connections:
            logger.info(f"Closing {len(active_connections)} active connections...")
            close_tasks = []
            for writer in list(active_connections):
                writer.close()
                close_tasks.append(writer.wait_closed())

            try:
                await asyncio.wait_for(
                    asyncio.gather(*close_tasks, return_exceptions=True),
                    timeout=1.0
                )
            except asyncio.TimeoutError:
                logger.warning("Connection close timeout - forcing shutdown")

        logger.info("Shutdown complete")

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())
