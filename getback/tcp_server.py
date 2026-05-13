"""TCP server implementation with command-based protocol."""

import asyncio
import logging
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
            - ("immediate", 0) for all other commands
    """
    command = data.strip()

    if command.upper() == "OPEN":
        return ("persistent", None)

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
        command = data.decode('utf-8')
        logger.info(f"TCP command from {addr}: {command.strip()}")

        # Parse command to determine connection lifetime
        mode, duration = parse_tcp_command(command)

        # Increment counter and respond
        value = await counter.increment()
        logger.info(f"TCP counter: {value} (server: {server_id}, mode: {mode})")

        response = f"{value} ({server_id})\n".encode('utf-8')
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
    server_id: str
) -> None:
    """Start TCP server.

    Args:
        host: Bind address
        port: Port number
        counter: Counter instance for this server
        active_connections: Set to track persistent connections
        server_id: Server identifier to include in responses
    """
    async def handler(reader, writer):
        await tcp_handler(reader, writer, counter, active_connections, server_id)

    server = await asyncio.start_server(handler, host, port)
    addr = server.sockets[0].getsockname()
    logger.info(f"✓ TCP ready on {addr[0]}:{addr[1]}")

    async with server:
        await server.serve_forever()
