#!/usr/bin/env python3
"""Simple HTTP client for Get-Back counter service."""

import sys
import urllib.request
import urllib.error


def main():
    if len(sys.argv) < 2:
        print("Usage: python http_client.py <url>")
        print("Example: python http_client.py http://localhost:9091/")
        sys.exit(1)

    url = sys.argv[1]

    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            counter = response.read().decode('utf-8').strip()
            print(f"Counter: {counter}")
    except urllib.error.URLError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except TimeoutError:
        print("Error: Request timed out")
        sys.exit(1)


if __name__ == "__main__":
    main()
