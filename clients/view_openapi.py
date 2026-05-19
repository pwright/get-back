#!/usr/bin/env python3
"""View OpenAPI spec from Get-Back dashboard."""

import sys
import json
import urllib.request
import urllib.error


def main():
    if len(sys.argv) < 2:
        print("Usage: python view_openapi.py <dashboard-url>")
        print("\nExample:")
        print("  python view_openapi.py http://localhost:9093")
        print("\nOutput:")
        print("  Fetches and pretty-prints the OpenAPI 3.0 specification")
        print("  Save to file: python view_openapi.py http://localhost:9093 > openapi.json")
        sys.exit(1)

    dashboard_url = sys.argv[1].rstrip('/')
    openapi_url = f"{dashboard_url}/openapi.json"

    try:
        with urllib.request.urlopen(openapi_url, timeout=5) as response:
            spec = json.loads(response.read().decode('utf-8'))

            # Pretty print to stdout
            print(json.dumps(spec, indent=2))

            # Also print summary to stderr so it doesn't interfere with JSON output
            info = spec.get('info', {})
            paths = spec.get('paths', {})

            print("\n" + "="*60, file=sys.stderr)
            print(f"API: {info.get('title', 'Unknown')}", file=sys.stderr)
            print(f"Version: {info.get('version', 'Unknown')}", file=sys.stderr)
            print(f"Endpoints: {len(paths)}", file=sys.stderr)
            print("="*60, file=sys.stderr)
            print("\nEndpoints:", file=sys.stderr)
            for path, methods in paths.items():
                for method in methods.keys():
                    if method in ['get', 'post', 'put', 'delete', 'patch']:
                        summary = methods[method].get('summary', 'No description')
                        print(f"  {method.upper():6s} {path:40s} {summary}", file=sys.stderr)
            print(file=sys.stderr)

    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code}: {e.reason}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Connection Error: {e.reason}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Invalid JSON response: {e}", file=sys.stderr)
        sys.exit(1)
    except TimeoutError:
        print("Error: Request timed out", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nAborted", file=sys.stderr)
        sys.exit(130)


if __name__ == "__main__":
    main()
