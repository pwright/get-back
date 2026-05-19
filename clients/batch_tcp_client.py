#!/usr/bin/env python3
"""Batch TCP client for Get-Back dashboard server (server-side batching)."""

import sys
import json
import urllib.request
import urllib.error
from collections import Counter


def main():
    if len(sys.argv) < 5:
        print("Usage: python batch_tcp_client.py <dashboard-url> <backend> <command> <amount>")
        print("\nArguments:")
        print("  dashboard-url   Dashboard server URL (e.g., http://localhost:9093)")
        print("  backend         Backend to target (e.g., mkl-backend-tcp:9092)")
        print("  command         TCP command (number for timed, OPEN for persistent, other for immediate)")
        print("  amount          Number of requests to send (e.g., 1000)")
        print("\nExamples:")
        print("  python batch_tcp_client.py http://localhost:9093 mkl-backend-tcp:9092 test 1000")
        print("  python batch_tcp_client.py http://localhost:9093 localhost:9092 OPEN 100")
        print("  python batch_tcp_client.py http://localhost:9093 getback:9092 5 500")
        sys.exit(1)

    dashboard_url = sys.argv[1].rstrip('/')
    backend = sys.argv[2]
    command = sys.argv[3]
    amount = int(sys.argv[4])

    # Build request
    api_url = f"{dashboard_url}/api/request/tcp"
    request_data = {
        "backend": backend,
        "command": command,
        "amount": amount
    }

    print(f"Sending {amount} TCP '{command}' requests to {backend} via {dashboard_url}...")

    try:
        # Make request to dashboard
        req = urllib.request.Request(
            api_url,
            data=json.dumps(request_data).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )

        with urllib.request.urlopen(req, timeout=60) as response:
            data = json.loads(response.read().decode('utf-8'))

            results = data.get('results', [])
            total = data.get('total', 0)
            successful = data.get('successful', 0)

            print(f"\n{'='*60}")
            print(f"Batch Results")
            print(f"{'='*60}")
            print(f"Total requested:  {total}")
            print(f"Successful:       {successful}")
            print(f"Failed:           {total - successful}")

            if results:
                # Calculate latency stats
                latencies = [r['latency_ms'] for r in results]
                latencies.sort()
                min_lat = min(latencies)
                max_lat = max(latencies)
                avg_lat = sum(latencies) // len(latencies)
                p50_lat = latencies[len(latencies) // 2]
                p95_lat = latencies[int(len(latencies) * 0.95)]
                p99_lat = latencies[int(len(latencies) * 0.99)]

                print(f"\nLatency Statistics:")
                print(f"  Min:  {min_lat}ms    P50:  {p50_lat}ms    P95:  {p95_lat}ms")
                print(f"  Max:  {max_lat}ms    Avg:  {avg_lat}ms    P99:  {p99_lat}ms")

                # Show distribution across servers
                server_counts = Counter(r['server'] for r in results)
                print(f"\nDistribution across servers:")
                for server, count in server_counts.most_common():
                    percent = (count / len(results)) * 100
                    print(f"  {server:40s}  {count:5d} requests  ({percent:5.1f}%)")

                print(f"\nUnique servers:   {len(server_counts)}")

    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code}: {e.reason}")
        try:
            error_body = e.read().decode('utf-8')
            print(f"Response: {error_body}")
        except Exception:
            pass
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
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nAborted")
        sys.exit(130)


if __name__ == "__main__":
    main()
