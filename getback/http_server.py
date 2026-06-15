"""HTTP server implementation with counter endpoint."""

import asyncio
import json
import logging
import ssl
import time
from typing import Optional
from .counter import Counter


logger = logging.getLogger(__name__)


def parse_http_request(data: bytes) -> str:
    """Parse HTTP request to extract the path.

    Args:
        data: Raw HTTP request bytes

    Returns:
        Request path (e.g., "/", "/health"), defaults to "/" if parsing fails
    """
    try:
        request_line = data.decode('utf-8').split('\r\n')[0]
        parts = request_line.split(' ')
        if len(parts) >= 2:
            return parts[1]  # e.g., "GET /health HTTP/1.1" -> "/health"
    except Exception:
        pass
    return "/"


def format_http_response(body: str, content_type: str = "text/plain") -> bytes:
    """Format HTTP/1.0 response.

    Args:
        body: Response body content
        content_type: Content-Type header value

    Returns:
        Complete HTTP response as bytes
    """
    return f"HTTP/1.0 200 OK\r\nContent-Type: {content_type}\r\n\r\n{body}\n".encode('utf-8')


async def http_handler(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    counter: Counter,
    server_id: str
) -> None:
    """Handle individual HTTP connection.

    Args:
        reader: Async stream reader
        writer: Async stream writer
        counter: Counter instance to increment
        server_id: Server identifier to include in response
    """
    addr = writer.get_extra_info('peername')
    logger.info(f"HTTP connection from {addr}")

    try:
        # Read until end of HTTP headers
        data = await reader.readuntil(b'\r\n\r\n')
        path = parse_http_request(data)

        # Health endpoint doesn't increment counter
        if path == '/health':
            body = "OK"
            response = format_http_response(body, content_type="text/plain")
            logger.debug(f"HTTP health check from {addr}")
        else:
            value = await counter.increment()
            logger.info(f"HTTP counter: {value} (server: {server_id}, path: {path})")

            # Generate JSON response with timestamp
            response_data = {
                "counter": value,
                "server": server_id,
                "timestamp": int(time.time() * 1000)  # Milliseconds
            }
            body = json.dumps(response_data, separators=(',', ':'))
            response = format_http_response(body, content_type="application/json")
        writer.write(response)
        await writer.drain()

    except asyncio.IncompleteReadError:
        logger.warning(f"HTTP incomplete request from {addr}")
    except Exception as e:
        logger.error(f"HTTP error from {addr}: {e}")
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass
        logger.debug(f"HTTP connection closed: {addr}")


async def start_http_server(
    host: str,
    port: int,
    counter: Counter,
    server_id: str,
    ssl_context: Optional[ssl.SSLContext] = None
) -> None:
    """Start HTTP server.

    Args:
        host: Bind address
        port: Port number
        counter: Counter instance for this server
        server_id: Server identifier to include in responses
        ssl_context: Optional SSL context for TLS support
    """
    async def handler(reader, writer):
        await http_handler(reader, writer, counter, server_id)

    server = await asyncio.start_server(handler, host, port, ssl=ssl_context)
    addr = server.sockets[0].getsockname()
    protocol = "HTTPS" if ssl_context else "HTTP"
    logger.info(f"✓ {protocol} ready on {addr[0]}:{addr[1]}")

    async with server:
        await server.serve_forever()
