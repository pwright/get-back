"""TCP server implementation with command-based protocol."""

import asyncio
import json
import logging
import ssl
import time
from typing import Optional, Tuple, Set
from .counter import Counter


logger = logging.getLogger(__name__)


def parse_tcp_command(data: str) -> Tuple[str, Optional[int]]:
    """Parse TCP command and determine connection lifetime.

    Args:
        data: Command string from client

    Returns:
        Tuple of (mode, duration) where:
            - ("timed", N) for numeric commands (stay open N seconds)
            - ("persistent", None) for "OPEN" command
            - ("half_close_send", None) for "HALF_CLOSE_SEND" (send response, shutdown write, read until EOF)
            - ("half_close_read", None) for "HALF_CLOSE_READ" (read until EOF, send response, close)
            - ("immediate", 0) for all other commands
    """
    command = data.strip()

    if command.upper() == "OPEN":
        return ("persistent", None)

    if command.upper() == "HALF_CLOSE_SEND":
        return ("half_close_send", None)

    if command.upper() == "HALF_CLOSE_READ":
        return ("half_close_read", None)

    try:
        duration = int(command)
        if duration > 0:
            return ("timed", duration)
    except ValueError:
        pass

    return ("immediate", 0)


async def tcp_handler(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    counter: Counter,
    active_connections: Set[asyncio.StreamWriter],
    server_id: str
) -> None:
    """Handle individual TCP connection.

    Args:
        reader: Async stream reader
        writer: Async stream writer
        counter: Counter instance to increment
        active_connections: Set of persistent connections
        server_id: Server identifier to include in response
    """
    addr = writer.get_extra_info('peername')
    logger.info(f"TCP connection from {addr}")

    try:
        # Read command (line-delimited)
        data = await reader.readline()
        try:
            command = data.decode('utf-8')
        except UnicodeDecodeError:
            logger.warning(f"TCP non-UTF-8 data from {addr} (TLS client connecting to plain TCP?)")
            return
        logger.info(f"TCP command from {addr}: {command.strip()}")

        # Parse command to determine connection lifetime
        mode, duration = parse_tcp_command(command)

        # Increment counter and respond
        value = await counter.increment()
        logger.info(f"TCP counter: {value} (server: {server_id}, mode: {mode})")

        # Generate JSON response with timestamp
        response_data = {
            "counter": value,
            "server": server_id,
            "timestamp": int(time.time() * 1000)  # Milliseconds
        }
        response = (json.dumps(response_data, separators=(',', ':')) + "\n").encode('utf-8')
        writer.write(response)
        await writer.drain()

        # Honor timing directive
        if mode == "timed":
            await asyncio.sleep(duration)
        elif mode == "persistent":
            active_connections.add(writer)
            try:
                # Wait until client closes connection
                while True:
                    data = await reader.read(1024)
                    if not data:
                        break
            finally:
                active_connections.discard(writer)
        elif mode == "half_close_send":
            # Half-close: send response, shutdown write side, keep reading until client closes
            logger.info(f"TCP half-close (send): shutting down write side for {addr}")
            try:
                writer.write_eof()  # Send FIN on write side
                await writer.drain()
            except OSError as e:
                logger.warning(f"TCP half-close write_eof failed for {addr}: {e}")
            # Keep reading until client closes
            try:
                while True:
                    data = await reader.read(1024)
                    if not data:
                        logger.info(f"TCP half-close (send): received EOF from client {addr}")
                        break
            except Exception as e:
                logger.warning(f"TCP half-close (send) read error from {addr}: {e}")
        elif mode == "half_close_read":
            # Half-close: read until client sends FIN, then send response
            logger.info(f"TCP half-close (read): waiting for client EOF from {addr}")
            try:
                while True:
                    data = await reader.read(1024)
                    if not data:
                        logger.info(f"TCP half-close (read): received EOF from client {addr}")
                        break
                    logger.debug(f"TCP half-close (read): received {len(data)} bytes from {addr}")
            except Exception as e:
                logger.warning(f"TCP half-close (read) error from {addr}: {e}")
            # Client has closed write side, now send response and close normally
            # (response was already sent above, so just let finally block close)
        # immediate mode: close right away

    except asyncio.IncompleteReadError:
        logger.warning(f"TCP incomplete read from {addr}")
    except Exception as e:
        logger.error(f"TCP error from {addr}: {e}")
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass
        logger.debug(f"TCP connection closed: {addr}")


async def start_tcp_server(
    host: str,
    port: int,
    counter: Counter,
    active_connections: Set[asyncio.StreamWriter],
    server_id: str,
    ssl_context: Optional[ssl.SSLContext] = None
) -> None:
    """Start TCP server.

    Args:
        host: Bind address
        port: Port number
        counter: Counter instance for this server
        active_connections: Set to track persistent connections
        server_id: Server identifier to include in responses
        ssl_context: Optional SSL context for TLS support
    """
    async def handler(reader, writer):
        await tcp_handler(reader, writer, counter, active_connections, server_id)

    server = await asyncio.start_server(handler, host, port, ssl=ssl_context)
    addr = server.sockets[0].getsockname()
    protocol = "TLS-TCP" if ssl_context else "TCP"
    logger.info(f"✓ {protocol} ready on {addr[0]}:{addr[1]}")

    async with server:
        await server.serve_forever()
