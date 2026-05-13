#!/usr/bin/env python3
"""TCP client for Get-Back counter service."""

import sys
import socket
import time


def main():
    if len(sys.argv) < 4:
        print("Usage: python tcp_client.py <host> <port> <command>")
        print("\nCommands:")
        print("  <number>  - Stay open for N seconds (e.g., '5')")
        print("  OPEN      - Persistent connection (Ctrl+C to close)")
        print("  <other>   - Any other text closes immediately")
        print("\nExamples:")
        print("  python tcp_client.py localhost 9092 test")
        print("  python tcp_client.py localhost 9092 5")
        print("  python tcp_client.py localhost 9092 OPEN")
        sys.exit(1)

    host = sys.argv[1]
    port = int(sys.argv[2])
    command = sys.argv[3]

    start_time = time.time()

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((host, port))
            print(f"Connected to {host}:{port}")

            # Send command
            sock.sendall(f"{command}\n".encode('utf-8'))

            # Receive response
            response = sock.recv(1024).decode('utf-8').strip()
            print(f"Counter: {response}")

            if command.upper() == "OPEN":
                print("Connection persistent (Ctrl+C to close)...")
                try:
                    # Wait for user interrupt
                    while True:
                        time.sleep(1)
                except KeyboardInterrupt:
                    print("\nClosing connection...")
            # Otherwise connection closes automatically

            duration = time.time() - start_time
            print(f"Duration: {duration:.2f}s")

    except ConnectionRefusedError:
        print(f"Error: Connection refused to {host}:{port}")
        sys.exit(1)
    except socket.timeout:
        print("Error: Connection timed out")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
