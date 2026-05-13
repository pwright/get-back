"""Main entry point for Get-Back service."""

import asyncio
import signal
import time
from . import setup_logging
from .cli import parse_args
from .counter import Counter
from .http_server import start_http_server
from .tcp_server import start_tcp_server
from .dashboard_server import start_dashboard_server


async def main():
    """Start both HTTP and TCP servers concurrently."""
    # Parse configuration
    config = parse_args()

    # Setup logging
    logger = setup_logging(config.log_level)

    logger.info(f"Starting Get-Back | HTTP:{config.http_port} TCP:{config.tcp_port} Dashboard:{config.dashboard_port}")

    # Create independent counters for each protocol
    http_counter = Counter()
    tcp_counter = Counter()
    active_connections = set()
    start_time = time.time()

    # Graceful shutdown handler
    shutdown_event = asyncio.Event()

    def handle_shutdown(sig, frame):
        logger.info(f"\nReceived signal {sig}, shutting down gracefully...")
        shutdown_event.set()

    # Register signal handlers
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    try:
        # Start all three servers concurrently
        http_task = asyncio.create_task(
            start_http_server(config.host, config.http_port, http_counter, config.server_id)
        )
        tcp_task = asyncio.create_task(
            start_tcp_server(config.host, config.tcp_port, tcp_counter, active_connections, config.server_id)
        )
        dashboard_task = asyncio.create_task(
            start_dashboard_server(config.host, config.dashboard_port, http_counter, tcp_counter, start_time, config.backend_host)
        )

        # Wait for shutdown signal
        await shutdown_event.wait()

        # Cancel server tasks
        http_task.cancel()
        tcp_task.cancel()
        dashboard_task.cancel()

        # Close all active persistent connections
        for writer in list(active_connections):
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

        logger.info("Shutdown complete")

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())
