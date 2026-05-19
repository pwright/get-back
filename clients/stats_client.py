#!/usr/bin/env python3
"""Stats client for Get-Back dashboard server."""

import sys
import json
import urllib.request
import urllib.error


def format_uptime(seconds):
    """Format uptime in human-readable format."""
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60

    if h > 0:
        return f"{h}h {m}m {s}s"
    elif m > 0:
        return f"{m}m {s}s"
    else:
        return f"{s}s"


def print_latency(label, latency_data):
    """Print latency statistics in tabular format."""
    if not latency_data:
        print(f"\n{label} Latency: No data")
        return

    count = latency_data.get('count', 0)
    print(f"\n{label} Latency ({count} samples):")
    print(f"  Min:  {latency_data['min']}ms    P50:  {latency_data['p50']}ms    P95:  {latency_data['p95']}ms")
    print(f"  Max:  {latency_data['max']}ms    Avg:  {latency_data['avg']}ms    P99:  {latency_data['p99']}ms")


def main():
    if len(sys.argv) < 2:
        print("Usage: python stats_client.py <dashboard-url>")
        print("Example: python stats_client.py http://localhost:9093")
        sys.exit(1)

    base_url = sys.argv[1].rstrip('/')
    stats_url = f"{base_url}/stats"

    try:
        with urllib.request.urlopen(stats_url, timeout=5) as response:
            data = json.loads(response.read().decode('utf-8'))

            # Header
            print(f"\nDashboard Stats ({base_url})")
            print("━" * 50)

            # Counters
            http_counter = data.get('http_counter', 0)
            tcp_counter = data.get('tcp_counter', 0)
            total = http_counter + tcp_counter

            print("\nCounters:")
            print(f"  HTTP:  {http_counter}")
            print(f"  TCP:   {tcp_counter}")
            print(f"  Total: {total}")

            # Uptime
            uptime_seconds = data.get('uptime', 0)
            print(f"\nUptime: {format_uptime(uptime_seconds)}")

            # Latency stats
            latency = data.get('latency', {})
            http_latency = latency.get('http', {})
            tcp_latency = latency.get('tcp', {})

            print_latency("HTTP", http_latency)
            print_latency("TCP", tcp_latency)

            print()  # Trailing newline

    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code}: {e.reason}")
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Connection Error: {e.reason}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Invalid JSON response: {e}")
        sys.exit(1)
    except TimeoutError:
        print("Error: Request timed out")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nAborted")
        sys.exit(130)


if __name__ == "__main__":
    main()
