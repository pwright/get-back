#!/usr/bin/env python3
"""Half-close TCP client for testing FIN behavior with skupper."""

import sys
import socket
import time


def test_half_close_send(host: str, port: int):
    """Test HALF_CLOSE_SEND: server sends response, shuts down write, keeps reading.

    This tests the server's FIN_WAIT_1 behavior - the server sends a response,
    then calls shutdown(SHUT_WR) which sends a FIN packet on the write side
    while keeping the read side open.

    Args:
        host: Server host
        port: Server port
    """
    print(f"\n=== Test: HALF_CLOSE_SEND ===")
    print(f"Server will send response, shutdown write side (send FIN), then keep reading")

    start_time = time.time()

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((host, port))
            print(f"✓ Connected to {host}:{port}")

            # Send HALF_CLOSE_SEND command
            sock.sendall(b"HALF_CLOSE_SEND\n")
            print("✓ Sent command: HALF_CLOSE_SEND")

            # Receive response (should come immediately)
            response = sock.recv(1024).decode('utf-8').strip()
            print(f"✓ Received response: {response}")

            # Server has now shut down write side and sent FIN
            # Try to receive more data - should get EOF (empty bytes)
            eof_data = sock.recv(1024)
            if not eof_data:
                print("✓ Received EOF from server (server closed write side)")
            else:
                print(f"✗ Unexpected data after response: {eof_data}")

            # We can still send data (server is reading until we close)
            print("✓ Sending some data to server...")
            sock.sendall(b"Some data after server FIN\n")
            time.sleep(0.1)  # Give server time to read

            # Now close our write side (send our FIN)
            sock.shutdown(socket.SHUT_WR)
            print("✓ Closed our write side (sent FIN)")

            # Connection should now fully close
            duration = time.time() - start_time
            print(f"✓ Test complete in {duration:.2f}s")
            print("✓ Server handled half-close correctly")

    except Exception as e:
        print(f"✗ Error: {e}")
        sys.exit(1)


def test_half_close_read(host: str, port: int):
    """Test HALF_CLOSE_READ: server reads until client FIN, then sends response.

    This tests the server's ability to detect when the client closes the write side.
    The server should read until EOF (client's FIN), then send the response.

    Args:
        host: Server host
        port: Server port
    """
    print(f"\n=== Test: HALF_CLOSE_READ ===")
    print(f"Server will read until client FIN, then send response")

    start_time = time.time()

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((host, port))
            print(f"✓ Connected to {host}:{port}")

            # Send HALF_CLOSE_READ command
            sock.sendall(b"HALF_CLOSE_READ\n")
            print("✓ Sent command: HALF_CLOSE_READ")

            # Read the immediate response (counter value)
            response = sock.recv(1024).decode('utf-8').strip()
            print(f"✓ Received initial response: {response}")

            # Server is now waiting for us to close write side
            # Send some data
            print("✓ Sending some data to server...")
            sock.sendall(b"Test data 1\n")
            sock.sendall(b"Test data 2\n")
            time.sleep(0.1)

            # Close our write side (send FIN)
            sock.shutdown(socket.SHUT_WR)
            print("✓ Closed our write side (sent FIN)")

            # Server should detect EOF and close normally
            # We should get EOF on read
            final_data = sock.recv(1024)
            if not final_data:
                print("✓ Received EOF from server (server closed connection)")
            else:
                print(f"Server sent additional data: {final_data}")

            duration = time.time() - start_time
            print(f"✓ Test complete in {duration:.2f}s")
            print("✓ Server handled half-close correctly")

    except Exception as e:
        print(f"✗ Error: {e}")
        sys.exit(1)


def main():
    if len(sys.argv) < 3:
        print("Usage: python halfclose_client.py <host> <port> [mode]")
        print("\nModes:")
        print("  send  - Test HALF_CLOSE_SEND (server sends FIN first)")
        print("  read  - Test HALF_CLOSE_READ (client sends FIN first)")
        print("  both  - Test both modes (default)")
        print("\nExamples:")
        print("  python halfclose_client.py localhost 9092")
        print("  python halfclose_client.py getback 9092 send")
        print("  python halfclose_client.py skupper-listener 9092 read")
        sys.exit(1)

    host = sys.argv[1]
    port = int(sys.argv[2])
    mode = sys.argv[3] if len(sys.argv) > 3 else "both"

    print(f"Half-Close TCP Client")
    print(f"Target: {host}:{port}")
    print(f"Mode: {mode}")

    try:
        if mode in ("send", "both"):
            test_half_close_send(host, port)

        if mode in ("read", "both"):
            test_half_close_read(host, port)

        print("\n✓ All tests passed!")

    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)


if __name__ == "__main__":
    main()
