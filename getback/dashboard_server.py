"""Dashboard server for observability on port 9093."""

import asyncio
import logging
import json
import time
from typing import Dict, Any
from .counter import Counter


logger = logging.getLogger(__name__)


def generate_openapi_spec(backend_host: str = 'localhost') -> dict:
    """Generate OpenAPI 3.0 specification for dashboard API.

    Args:
        backend_host: Default backend host

    Returns:
        OpenAPI spec dict
    """
    return {
        "openapi": "3.0.0",
        "info": {
            "title": "Get-Back Dashboard API",
            "version": "1.0.0",
            "description": "Interactive dashboard API for testing load balancing and service mesh configurations. Supports server-side batching for high-volume testing.",
            "contact": {
                "name": "Get-Back Project",
                "url": "https://github.com/yourusername/get-back"
            }
        },
        "servers": [
            {
                "url": "/",
                "description": "Dashboard server"
            }
        ],
        "paths": {
            "/api/request/http": {
                "post": {
                    "summary": "Make HTTP requests to backend (server-side batching)",
                    "description": "Send N concurrent HTTP requests to a backend service. The dashboard server handles batching internally.",
                    "tags": ["Requests"],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["backend", "amount"],
                                    "properties": {
                                        "backend": {
                                            "type": "string",
                                            "description": "Backend host:port (e.g., 'getback:9091', 'mkl-backend-http:9091')",
                                            "example": f"{backend_host}:9091"
                                        },
                                        "amount": {
                                            "type": "integer",
                                            "description": "Number of concurrent requests to make",
                                            "minimum": 1,
                                            "maximum": 10000,
                                            "example": 10
                                        }
                                    }
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "Batch request completed",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "results": {
                                                "type": "array",
                                                "items": {
                                                    "$ref": "#/components/schemas/RequestResult"
                                                }
                                            },
                                            "total": {
                                                "type": "integer",
                                                "description": "Total requests attempted"
                                            },
                                            "successful": {
                                                "type": "integer",
                                                "description": "Number of successful requests"
                                            }
                                        }
                                    }
                                }
                            }
                        },
                        "502": {
                            "description": "Backend error or invalid response",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/Error"
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "/api/request/tcp": {
                "post": {
                    "summary": "Make TCP requests to backend (server-side batching)",
                    "description": "Send N concurrent TCP requests to a backend service with command-based protocol.",
                    "tags": ["Requests"],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["backend", "command", "amount"],
                                    "properties": {
                                        "backend": {
                                            "type": "string",
                                            "description": "Backend host:port (e.g., 'getback:9092')",
                                            "example": f"{backend_host}:9092"
                                        },
                                        "command": {
                                            "type": "string",
                                            "description": "TCP command: numeric (timed), 'OPEN' (persistent), or other (immediate close)",
                                            "example": "test"
                                        },
                                        "amount": {
                                            "type": "integer",
                                            "description": "Number of concurrent requests to make",
                                            "minimum": 1,
                                            "maximum": 10000,
                                            "example": 10
                                        }
                                    }
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "Batch request completed",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "results": {
                                                "type": "array",
                                                "items": {
                                                    "$ref": "#/components/schemas/TCPRequestResult"
                                                }
                                            },
                                            "total": {
                                                "type": "integer"
                                            },
                                            "successful": {
                                                "type": "integer"
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "/stats": {
                "get": {
                    "summary": "Get dashboard statistics",
                    "description": "Returns dashboard server counters, uptime, and latency aggregates for backend requests.",
                    "tags": ["Metrics"],
                    "responses": {
                        "200": {
                            "description": "Server statistics",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/Stats"
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "/api/distribution": {
                "get": {
                    "summary": "Get request distribution",
                    "description": "Returns server-side distribution tracking showing request counts per backend server.",
                    "tags": ["Metrics"],
                    "responses": {
                        "200": {
                            "description": "Distribution data",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/Distribution"
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "/api/distribution/reset": {
                "post": {
                    "summary": "Reset distribution counts",
                    "description": "Clears server-side distribution tracking data.",
                    "tags": ["Metrics"],
                    "responses": {
                        "200": {
                            "description": "Distribution reset",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "message": {"type": "string"},
                                            "cleared": {"type": "integer"},
                                            "timestamp": {"type": "integer"}
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "/api/connections/close-all": {
                "post": {
                    "summary": "Close all persistent TCP connections and stop cycling",
                    "description": "Closes all active persistent TCP connections opened by the dashboard to backends. If cycling is active, stops the cycle loop before closing connections.",
                    "tags": ["Connections"],
                    "responses": {
                        "200": {
                            "description": "Connections closed and cycling stopped if active",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "message": {"type": "string"},
                                            "closed": {"type": "integer", "description": "Number of connections closed"},
                                            "cycling_stopped": {"type": "boolean", "description": "Whether cycling was stopped"},
                                            "timestamp": {"type": "integer"}
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "/api/connections/cycle": {
                "post": {
                    "summary": "Cycle TCP connections (continuous ramp up and down)",
                    "description": "Continuously cycles TCP connections: ramps up over 20 seconds to 'amount' connections, then ramps down over 20 seconds to zero, and repeats. Cycling continues until stopped by calling /api/connections/close-all. Each cycle takes 40 seconds.",
                    "tags": ["Connections"],
                    "requestBody": {
                        "required": true,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "backend": {
                                            "type": "string",
                                            "description": "Backend server (host:port)",
                                            "example": f"{backend_host}:9092"
                                        },
                                        "amount": {
                                            "type": "integer",
                                            "description": "Peak number of connections (max 1000)",
                                            "minimum": 1,
                                            "maximum": 1000,
                                            "example": 50
                                        }
                                    },
                                    "required": ["backend", "amount"]
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "Cycle started",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "message": {"type": "string"},
                                            "amount": {"type": "integer", "description": "Peak connections per cycle"},
                                            "cycle_duration": {"type": "integer", "description": "Duration per cycle in seconds"},
                                            "info": {"type": "string", "description": "Information about stopping the cycle"},
                                            "timestamp": {"type": "integer"}
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },
        "components": {
            "schemas": {
                "RequestResult": {
                    "type": "object",
                    "properties": {
                        "counter": {
                            "type": "integer",
                            "description": "Backend counter value"
                        },
                        "server": {
                            "type": "string",
                            "description": "Backend server hostname/pod name"
                        },
                        "latency_ms": {
                            "type": "integer",
                            "description": "Request latency in milliseconds"
                        },
                        "timestamp": {
                            "type": "integer",
                            "description": "Unix timestamp"
                        }
                    }
                },
                "TCPRequestResult": {
                    "allOf": [
                        {"$ref": "#/components/schemas/RequestResult"},
                        {
                            "type": "object",
                            "properties": {
                                "command": {
                                    "type": "string",
                                    "description": "TCP command sent"
                                }
                            }
                        }
                    ]
                },
                "Stats": {
                    "type": "object",
                    "properties": {
                        "http_counter": {
                            "type": "integer",
                            "description": "Dashboard's HTTP server counter"
                        },
                        "tcp_counter": {
                            "type": "integer",
                            "description": "Dashboard's TCP server counter"
                        },
                        "active_tcp_connections": {
                            "type": "integer",
                            "description": "Number of active persistent TCP connections (dashboard → backends)"
                        },
                        "uptime": {
                            "type": "integer",
                            "description": "Server uptime in seconds"
                        },
                        "timestamp": {
                            "type": "integer",
                            "description": "Unix timestamp"
                        },
                        "latency": {
                            "type": "object",
                            "properties": {
                                "http": {"$ref": "#/components/schemas/LatencyStats"},
                                "tcp": {"$ref": "#/components/schemas/LatencyStats"}
                            }
                        }
                    }
                },
                "LatencyStats": {
                    "type": "object",
                    "properties": {
                        "min": {"type": "integer", "description": "Minimum latency (ms)"},
                        "max": {"type": "integer", "description": "Maximum latency (ms)"},
                        "avg": {"type": "integer", "description": "Average latency (ms)"},
                        "p50": {"type": "integer", "description": "50th percentile (ms)"},
                        "p95": {"type": "integer", "description": "95th percentile (ms)"},
                        "p99": {"type": "integer", "description": "99th percentile (ms)"},
                        "count": {"type": "integer", "description": "Number of samples (max 1000)"}
                    }
                },
                "Distribution": {
                    "type": "object",
                    "properties": {
                        "distribution": {
                            "type": "object",
                            "additionalProperties": {
                                "type": "object",
                                "properties": {
                                    "count": {"type": "integer"},
                                    "percent": {"type": "number"}
                                }
                            }
                        },
                        "total": {"type": "integer"},
                        "timestamp": {"type": "integer"}
                    }
                },
                "Error": {
                    "type": "object",
                    "properties": {
                        "error": {
                            "type": "string",
                            "description": "Error message"
                        }
                    }
                }
            }
        },
        "tags": [
            {
                "name": "Requests",
                "description": "Backend request operations (server-side batching)"
            },
            {
                "name": "Metrics",
                "description": "Dashboard metrics and distribution tracking"
            },
            {
                "name": "Connections",
                "description": "Persistent TCP connection management"
            }
        ]
    }


def render_dashboard_html(backend_host: str = 'localhost') -> str:
    """Render dashboard HTML with backend host embedded.

    Args:
        backend_host: Default backend host for requests

    Returns:
        HTML string with embedded configuration
    """
    html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>getback Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #1a1a1a;
            color: #e0e0e0;
            padding: 20px;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        .header-with-logo {
            display: flex;
            align-items: center;
            gap: 16px;
            margin-bottom: 10px;
        }
        .skupper-logo {
            width: 50px;
            height: 50px;
            flex-shrink: 0;
        }
        h1 {
            font-size: 2.5rem;
            margin: 0;
            background: linear-gradient(135deg, #38586c 0%, #5a8a9f 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .subtitle { color: #888; margin-bottom: 30px; font-size: 1.1rem; }
        .metrics {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .metric {
            background: #2a2a2a;
            border: 1px solid #3a3a3a;
            border-radius: 12px;
            padding: 24px;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .metric:hover {
            transform: translateY(-4px);
            box-shadow: 0 8px 16px rgba(0,0,0,0.3);
        }
        .metric-label {
            color: #888;
            font-size: 0.9rem;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 8px;
        }
        .metric-value {
            font-size: 3rem;
            font-weight: 700;
            line-height: 1;
            background: linear-gradient(135deg, #38586c 0%, #5a8a9f 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .metric.http .metric-value {
            background: linear-gradient(135deg, #38586c 0%, #5a8a9f 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .metric.tcp .metric-value {
            background: linear-gradient(135deg, #5a8a9f 0%, #7aacbf 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .metric-delta {
            color: #4caf50;
            font-size: 0.9rem;
            margin-top: 8px;
        }
        .status {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.85rem;
            font-weight: 600;
            background: #2e7d32;
            color: white;
        }
        .footer {
            text-align: center;
            color: #666;
            margin-top: 40px;
            font-size: 0.9rem;
        }
        /* Toast notifications */
        .toast-container {
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 1000;
            pointer-events: none;
        }
        .toast {
            background: #2a2a2a;
            border: 1px solid #3a3a3a;
            border-left: 4px solid #38586c;
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 10px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.5);
            pointer-events: auto;
            animation: slideIn 0.3s ease-out;
            min-width: 250px;
            max-width: 400px;
        }
        .toast.success { border-left-color: #4caf50; }
        .toast.error { border-left-color: #f44336; }
        .toast.info { border-left-color: #2196f3; }
        .toast-title {
            font-weight: 600;
            margin-bottom: 4px;
            color: #e0e0e0;
        }
        .toast-message {
            font-size: 0.9rem;
            color: #aaa;
        }
        @keyframes slideIn {
            from {
                transform: translateX(400px);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
        /* Button states */
        button:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            transform: none !important;
        }
        button.loading {
            position: relative;
            color: transparent;
        }
        button.loading::after {
            content: '';
            position: absolute;
            width: 16px;
            height: 16px;
            top: 50%;
            left: 50%;
            margin-left: -8px;
            margin-top: -8px;
            border: 2px solid #fff;
            border-radius: 50%;
            border-top-color: transparent;
            animation: spin 0.6s linear infinite;
        }
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        .config-and-controls {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 20px;
        }
        .config {
            background: #2a2a2a;
            border: 1px solid #3a3a3a;
            border-radius: 12px;
            padding: 24px;
        }
        .config h2 {
            font-size: 1.2rem;
            margin-bottom: 16px;
            color: #e0e0e0;
        }
        .config-row {
            display: grid;
            grid-template-columns: 120px 1fr auto;
            gap: 12px;
            align-items: center;
            margin-bottom: 12px;
        }
        .config-row label {
            color: #888;
            font-size: 0.9rem;
        }
        .config-row input {
            background: #1a1a1a;
            border: 1px solid #3a3a3a;
            border-radius: 6px;
            padding: 8px 12px;
            color: #e0e0e0;
            font-family: monospace;
            font-size: 0.9rem;
        }
        .config-row input:focus {
            outline: none;
            border-color: #38586c;
        }
        .config-row button {
            padding: 8px 16px;
            background: linear-gradient(135deg, #38586c 0%, #5a8a9f 100%);
            color: white;
            border: none;
            border-radius: 6px;
            font-weight: 600;
            cursor: pointer;
            font-size: 0.85rem;
        }
        .config-row button:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.3);
        }
        .controls {
            background: #2a2a2a;
            border: 1px solid #3a3a3a;
            border-radius: 12px;
            padding: 24px;
        }
        .controls h2 {
            font-size: 1.2rem;
            margin-bottom: 16px;
            color: #e0e0e0;
        }
        .button-group {
            display: flex;
            gap: 12px;
            flex-wrap: wrap;
            margin-bottom: 12px;
        }
        .button-group label {
            color: #888;
            font-size: 0.9rem;
            width: 100%;
            margin-bottom: 4px;
        }
        button {
            padding: 10px 20px;
            border: none;
            border-radius: 8px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
            font-size: 0.9rem;
        }
        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.3);
        }
        button.http {
            background: linear-gradient(135deg, #38586c 0%, #5a8a9f 100%);
            color: white;
        }
        button.tcp {
            background: linear-gradient(135deg, #5a8a9f 0%, #7aacbf 100%);
            color: white;
        }
        button.tcp.secondary {
            background: linear-gradient(135deg, #4a7080 0%, #6a9aaa 100%);
        }
        button.danger {
            background: linear-gradient(135deg, #c62828 0%, #e53935 100%);
            color: white;
        }
        button.danger:hover {
            background: linear-gradient(135deg, #b71c1c 0%, #c62828 100%);
        }
        .history {
            background: #2a2a2a;
            border: 1px solid #3a3a3a;
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 20px;
            max-height: 400px;
            overflow-y: auto;
        }
        .history h2 {
            font-size: 1.2rem;
            margin-bottom: 16px;
            color: #e0e0e0;
        }
        .history-entry {
            background: #1a1a1a;
            border: 1px solid #3a3a3a;
            border-radius: 8px;
            padding: 12px;
            margin-bottom: 8px;
            font-size: 0.85rem;
            display: grid;
            grid-template-columns: auto 1fr auto;
            gap: 12px;
            align-items: center;
        }
        .history-entry .time {
            color: #666;
            font-family: monospace;
        }
        .history-entry .protocol {
            padding: 2px 8px;
            border-radius: 4px;
            font-weight: 600;
            font-size: 0.75rem;
        }
        .history-entry .protocol.http {
            background: #38586c;
            color: white;
        }
        .history-entry .protocol.tcp {
            background: #5a8a9f;
            color: white;
        }
        .history-entry .details {
            color: #e0e0e0;
        }
        .history-entry .server {
            color: #38586c;
            font-weight: 600;
        }
        .history-entry .latency {
            color: #888;
            text-align: right;
        }
        .distribution {
            background: #2a2a2a;
            border: 1px solid #3a3a3a;
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 20px;
        }
        .distribution h2 {
            font-size: 1.2rem;
            margin-bottom: 16px;
            color: #e0e0e0;
        }
        .dist-entry {
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid #3a3a3a;
            font-size: 0.9rem;
        }
        .dist-entry:last-child {
            border-bottom: none;
            font-weight: 600;
            margin-top: 8px;
            padding-top: 12px;
            border-top: 2px solid #3a3a3a;
        }
        .dist-entry .server {
            color: #38586c;
            font-family: monospace;
            font-size: 0.85rem;
        }
        .dist-entry .count {
            color: #e0e0e0;
        }
        .dist-entry .percent {
            color: #888;
        }
        @media (max-width: 768px) {
            .config-and-controls {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="toast-container" id="toast-container"></div>

    <div class="container">
        <div class="header-with-logo">
            <img src="data:image/svg+xml;base64,PHN2ZyBpZD0iYXJ0d29yayIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIiB2aWV3Qm94PSIwIDAgMTAyNCAxNDgwIj48ZGVmcz48c3R5bGU+LmNscy0xe2ZpbGw6IzM1MzUzNTt9LmNscy0ye2ZpbGw6IzM4NTg2Yzt9LmNscy0ze2ZpbGw6I2Q1YzViNzt9LmNscy00e2ZpbGw6I2ZmZjt9PC9zdHlsZT48L2RlZnM+PHRpdGxlPnNrdXBwZXJsb2dvX3JnYl92ZXJ0X2RlZmF1bHQ8L3RpdGxlPjxwYXRoIGNsYXNzPSJjbHMtMSIgZD0iTTk5OS45MSwzODIuODJsLTEzLjYtMS4zNGMtMS43NS0uMjctMjIuNi0zLjY5LTUzLjM1LTIxLjgxLTE4LjgxLTExLjA5LTM3LjYtMjUuNDItNTUuODUtNDIuNjItMjMtMjEuNjQtNDUuMTUtNDcuODktNjUuOS03OEE2MDMuMDUsNjAzLjA1LDAsMCwwLDYyNS44Miw2NC44MkM1NDMuNzQsMTUuNjgsNDgxLjQ2LDUuMzUsNDY0LjMzLDMuMzVBMzI4LjcsMzI4LjcsMCwwLDAsNDI2LjQ5LDEsMjI2LjA2LDIyNi4wNiwwLDAsMCwzOTAsMy43OUMzNTYuNjcsOS4xOCwzMjguNSwyMi40NCwzMDYuMjQsNDMuMmMtMjAuNDYsMTkuMDktMzUuNjMsNDQuMzMtNDUuMSw3NS05LjcsMzEuNDctMTMuNTksNjkuNjUtMTEuNTQsMTEzLjQ4LDIsNDIuOTQtMi4yNSw5MS44LTEyLjMxLDE0MS4zMWE3MjkuNCw3MjkuNCwwLDAsMS00NS43NSwxNDQuODdjLTIwLjYxLDQ3LjA3LTQ0LjcyLDg3Ljg0LTcxLjY1LDEyMS4xOEM5Mi40Nyw2NzMsNjMuNjYsNjk3LjI1LDM0LjI1LDcxMS4xOEwyMS43Myw3MTcuMSwxLDcyNi45MWw3LjgyLDIxLjU2LDQuNzMsMTNjMS4zMywzLjY3LDEzLjg2LDM2LjY0LDQzLjU0LDY0LjY5LDguNDEsNy45NCwxOS45NCwxOC4xMywzNC41NiwyNi40MywxNy40Miw5Ljg4LDM1LjYsMTQuODksNTQsMTQuODlhMTA0LDEwNCwwLDAsMCwxNS42LTEuMThjNy4zLTEuMSwxNC43My0yLjQsMjIuMjMtMy44NiwwLDMyLjEsNS45LDcyLDIyLjk0LDEyMC40NSwyNCw2OC4zMiw1NC44NSwxMTMuMjYsOTEuNjUsMTMzLjU2YTk1LDk1LDAsMCwwLDMwLjQsMTAuOCw4NC44MSw4NC44MSwwLDAsMCwzNy44LTIuMjNjMTAuMjYtMywxOC40OS0xMS41LDIyLjU5LTIzLjM4YTU4LjIzLDU4LjIzLDAsMCwwLDIuODUtMjIuNTRjMTYuNzgsNC40MSwzNi41OSw4LjkzLDU4LjI5LDEyLjU1LDEzLjg5LDIuMzEsMjguNTgsNC4yNiw0My43MSw1LjU3YTE3MC41OCwxNzAuNTgsMCwwLDAsMTkuMzUsMjguNTljMi4yMywyLjYyLDQuNTcsNS4yLDcuMDksNy42OGE5Ny43MSw5Ny43MSwwLDAsMCw4LDcuMTksNzAuMjksNzAuMjksMCwwLDAsMjAsMTEuNDksNTAuNjYsNTAuNjYsMCwwLDAsMTIuMzgsMi44Yy4xLjk4LDIuMTcuMTgsMy4yOC4xOGwxLjY1LDAsMS42NS0uMDYuODMsMCwuNDIsMCwuNDksMGMuNjYsMCwxLjMyLS4xMywyLS4yM2EzMS4wNSwzMS4wNSwwLDAsMCwzLjkyLS44MywzNC4wOCwzNC4wOCwwLDAsMCwxMy4yNC03LjM0LDQ1Ljc0LDQ1Ljc0LDAsMCwwLDguMjktOS45NSw2Ni4zMiw2Ni4zMiwwLDAsMCw1LjE3LTEwLjIyLDkwLjIsOTAuMiwwLDAsMCwzLjQ2LTEwLjExLDE0MSwxNDEsMCwwLDAsNC0xOS45MnEuMzUtMi42OC42LTUuMzQsMTEuOTQtMi43MywyMy4wOS02LjM4YzM2Ljk0LTEyLjEyLDY3LjM1LTMxLjg1LDkwLjc4LTU4LjgzLDcuNjEsMjcuMiwyMC44NywzNC4zMywyOS44LDM1LjgyLjQ5LjA4LDEsLjE0LDEuNDIuMTksNy40LjgxLDE4LjYtMS4yNiwyOS45Mi0xNS42OSw3LjQ0LTkuNDgsMTQuMzItMjMuNDgsMjAuNDUtNDEuNiwyMS40OS02My41OCwxMi4xNi0xNDIuNjcsOS0xNjQuMjh2LS4wNmwtLjA5LS41MmMtLjQxLTIuNzgtLjctNC41LS43OC01aC0uMDZjLS44OC01LTIuNDQtMTMtNC4xNi0yMS40OSwyLjUxLTEuNjUsNS0zLjMxLDcuMzktNSwzNC44My0yNC41Miw1OS44OC01NC4zNiw3NC40Ni04OC42OWExODAuOTMsMTgwLjkzLDAsMCwwLDEzLjktODMuMjhjLS4yOS00LS43My04LjA3LTEuMy0xMnEyLjI1LDIsNC41MSwzLjczYzExLDguNDUsMjIuMzIsMTIuNzQsMzMuNjYsMTIuNzQsMTEuNTgsMCwxOS4wNy00LjYxLDIxLjA5LTZsNi43Ny00Ljc0LDEuMjUtOC4xN2MuMjgtMS43OSwyLjA3LTE1LS4zNy0zNC4xNGExMjIuNSwxMjIuNSwwLDAsMCwxMS4wOC0xMWMxNC42My0xNi41OSwyNS0zOC44MywzMS44My02OCw1LjYyLTI0LjEyLDguNjItNTIuMzcsOS4xOC04Ni4zNWwuMjMtMTQsLjM4LTIzLjJaIi8+PHBhdGggY2xhc3M9ImNscy0yIiBkPSJNOTgzLjQ4LDQwNi41MWMtLjk0LS4wOS05NS0xMC45My0xOTMtMTUzLjE4QTU3Ny43LDU3Ny43LDAsMCwwLDYxMi44OCw4Ni40M2MtNzcuNzctNDYuNTUtMTM1LjYtNTYuMjEtMTUxLjQ3LTU4LjA2LTI1LjY4LTMtNDcuNzMtMi45LTY3LjQzLjI5LTI4LjI3LDQuNTctNTIsMTUuNjctNzAuNTUsMzMtMTcuMiwxNi4wNS0zMC4wNiwzNy41OC0zOC4yMSw2NC04Ljg1LDI4LjY5LTEyLjM2LDY0LTEwLjQ1LDEwNC44OCwyLjEsNDUtMi4zMiw5Ni0xMi44LDE0Ny41MWE3NTQuNjgsNzU0LjY4LDAsMCwxLTQ3LjM1LDE1MGMtMjEuNTEsNDkuMTItNDYuNzksOTEuODEtNzUuMTMsMTI2LjlDMTA5LjY3LDY5MS43OSw3Ny44OSw3MTguMzksNDUsNzM0bC0xMi41MSw1LjkyLDQuNzIsMTNhMTU3LjgzLDE1Ny44MywwLDAsMCwzNy4xNyw1NWMxNy43NCwxNi43Niw0NS40NCwzOS4yMiw4My4xMywzMy41NCw1Ny4wNS04LjYsMTI0LjcxLTMwLjQyLDE3NC42OS00OC44My05LTIwLjkyLTEyLjM4LTQyLjUxLTEyLjg0LTYxLjgzLTExLjcyLDExLjU0LTI0LDIwLjM0LTMzLjcxLDI3LjI1LTUuMjEsMy43Mi0xMC4xMyw3LjIzLTEyLjU4LDkuNTVhMjcuNiwyNy42LDAsMCwxLTE5LDcuNzdjLTEyLjY3LDAtMjQtOC43NC0zMC4yLTIzLjM4LTEwLTIzLjM3LTguMjEtNjQuNiwyOS41MS0xMDMuODgsMzEtMzIuMjgsNDMuMjktNjAuODksNTIuMjYtODEuNzcsNS41Mi0xMi44NSw5Ljg4LTIzLDE3LjE5LTMwLjIzLDcuNjYtNy42LDE4LjkzLTExLjI5LDM0LjQzLTExLjI5LDExLjksMCwyNC44NCwyLjI0LDM0LjExLDQuMjcsMjMuMTMtMjYuMjEsNDcuOTItMzEuNTcsMTAwLTQyLjgzLDE3Ljc5LTMuODUsMzkuOTMtOC42NCw2Ny0xNS4yOCw4MC40Mi0xOS43NCwxMzAuNDEtMjMuODgsMTU4LjE5LTIzLjg4YTE5NC43NiwxOTQuNzYsMCwwLDEsMjMuMDgsMS4xOWM0LjM3LTIuNDQsMTMuMDYtNy40NywyOS44Ni0xNy42NCwxMy41OC04LjIyLDI1LjMzLTEzLjcsMzguNTYtMTMuNywyMS4zMywwLDM4LDEzLDc0LjU3LDQxLjM0LDYuMTEsNC43NCwxMywxMC4xMSwyMC41OSwxNS45MSwzNS41NiwyNy4yNyw1Mi41MSw1OS4xNCw2MC41OCw4NC4yNiwyMy41My0yOC4xMiwzMi40Mi03Ny43OCwzMy4zOC0xMzYuNTFsLjIzLTE0WiIvPjxwYXRoIGNsYXNzPSJjbHMtMyIgZD0iTTc4Ny4yOSw4NDYuMTRjLTEtNi4yOC0yLjE0LTEyLjQ5LTMuMzItMTguMzQtMzYsMTktNzkuNTksMzMuNzQtMTMwLjIsNDMuODMtNDksOS43OC05My4yOSwxNC43My0xMzEuNzEsMTQuNzMtNzUuMjMsMC0xMzAuNjgtMTguODItMTY0LjgtNTUuOTRhMTMxLjksMTMxLjksMCwwLDEtMTIuMzYtMTUuNjhjLTM1Ljc3LDEzLjMtODQuODMsMzAtMTMzLjQsNDEuNjItLjUyLDMwLjE4LDQsNzAuNDcsMjAuNTksMTE3LjU0LDEyLDM0LjExLDI1Ljc0LDYyLDQwLjg3LDgyLjc4LDEyLDE2LjQ5LDI0Ljg3LDI4LjYsMzguMjcsMzYsMTkuNzEsMTAuODcsMzYuNyw5LjQyLDQ3LjQ4LDYuMjgsMS4yMS0uMzYsMy4xMi0yLjE4LDQuNDktNi4xNiwyLjY0LTcuNjMsMi4zNy0yMS02LTM1LjM2aDBhNjEuMTQsNjEuMTQsMCwwLDEtMTAuODEsMi44OWMtMS44MS4yNS0zLjYyLjQ3LTUuNC42NXMtMy41OC4yMi01LjM1LjIyYTgzLjUyLDgzLjUyLDAsMCwxLTIwLjY3LTIuNTEsMTYzLjc1LDE2My43NSwwLDAsMCwxOS40Ni01LDYzLjUyLDYzLjUyLDAsMCwwLDE2LjctOC4xOWwxLjc5LTEuMjgsMS42NC0xLjRhNDAuMjcsNDAuMjcsMCwwLDAsMy0yLjkyLDUuNjgsNS42OCwwLDAsMCwuNjgtLjc4bC42Ni0uNzkuNjYtLjc5YTUuMzUsNS4zNSwwLDAsMCwuNjItLjhsMS4xNS0xLjY4YTkuMzgsOS4zOCwwLDAsMCwuNTctLjgzbC40OS0uODlhNDUuODEsNDUuODEsMCwwLDAsNS4zMi0xNS4zNSw4MS44LDgxLjgsMCwwLDAsLjgxLTE3LjQsMTY3LjY5LDE2Ny42OSwwLDAsMC0yLjA2LTE4LjIyLDMzNS45MSwzMzUuOTEsMCwwLDAtOS0zNy4wNmMtLjk1LTMuMS0xLjgzLTYuMi0yLjg1LTkuMjlsLTEuNDgtNC42NS0uNzQtMi4zMi0uNzQtMi4yMWExNjEuNTQsMTYxLjU0LDAsMCwwLTYuNzgtMTdjLTUuMTctMTAuOC0xMS42Ny0yMC41My0yMC4yNy0yNy40YTQ4LjMzLDQ4LjMzLDAsMCwwLTE0LjQ4LTgsNTcuNDgsNTcuNDgsMCwwLDAtMTcuMzYtMyw4Ny40OCw4Ny40OCwwLDAsMC0xOC45MiwxLjc0LDEyMy42OSwxMjMuNjksMCwwLDAtMTkuMjcsNS41LDYxLjMzLDYxLjMzLDAsMCwxLDcuODEtNi44Myw4Mi41NCw4Mi41NCwwLDAsMSw4LjgxLTUuNzIsNzYuNjEsNzYuNjEsMCwwLDEsMjAuMDYtNy44OUE2My4wNSw2My4wNSwwLDAsMSwzMTQsODU3LjA4YTU5LjU1LDU5LjU1LDAsMCwxLDExLjUyLDIuNjcsNjIsNjIsMCwwLDEsMTAuODcsNC45LDc0LjExLDc0LjExLDAsMCwxLDE4LjE5LDE0LjgyLDkwLjE0LDkwLjE0LDAsMCwxLDcuMTUsOC45NSwxMDkuNDksMTA5LjQ5LDAsMCwxLDYsOS40OSwxNDMuOSwxNDMuOSwwLDAsMSw5LjIyLDE5LjlsLjk1LDIuNTMuODUsMi40NSwxLjY5LDQuOWMuNTgsMS42MywxLjA4LDMuMywxLjYsNC45NWwxLjU0LDVhMjI2Ljc3LDIyNi43NywwLDAsMSw4LjUxLDQxLjQ0LDE0My44OCwxNDMuODgsMCwwLDEsLjQ5LDIxLjkyLDg4LjQ5LDg4LjQ5LDAsMCwxLTQuMTEsMjIuNDZjLS43LDEuODYtMS4zNCwzLjcxLTIuMTIsNS41NGwtMS4yOCwyLjcxYTI3LDI3LDAsMCwxLTEuMzgsMi42N0E0My44Niw0My44NiwwLDAsMSwzODAsMTA0MGMtLjA3Ljc3LS4xMywxLjQ4LS4yLDIuMjRxMS44NiwzLjA3LDMuNDQsNi4yMmE2MTguNiw2MTguNiwwLDAsMCw5Ny4zNSwyMC4wN3EtMi4zMi02LjA5LTQuMzEtMTIuM2MtMS0zLjA4LTEuOS02LjE4LTIuNzctOS4zcy0xLjY2LTYuMjUtMi4zNi05LjQxYTE1NS44MiwxNTUuODIsMCwwLDEtMy4yNy0xOS4xNGMzLjYzLDUuMzksNy4wOCwxMC43NywxMC41MywxNi4wOSwxLjc1LDIuNjUsMy40Miw1LjMyLDUuMTgsNy45NGw1LjE3LDcuODhjNi45LDEwLjQ0LDEzLjg0LDIwLjcsMjEuMDYsMzAuNTFhMjY1LjI3LDI2NS4yNywwLDAsMCwyMi42OCwyNy40N3EzLDMuMDksNi4wOCw1Ljg5YzIuMDcsMS44Niw0LjE1LDMuNjIsNi4yNSw1LjIxYTUxLjcsNTEuNywwLDAsMCwxMi42NSw3LjMsMjYuNTQsMjYuNTQsMCwwLDAsNiwxLjU1Yy40OCwwLDEsLjEzLDEuNDQuMTRsLjcxLjA2aDEuNzFhNS41MSw1LjUxLDAsMCwwLC43MS0uMDksNy40OCw3LjQ4LDAsMCwwLDMuMjgtMS41NSwyMS4xOSwyMS4xOSwwLDAsMCw0LjEzLTQuMjQsNDcuNjYsNDcuNjYsMCwwLDAsNC02LjMyYzEuMjUtMi4zMywyLjQzLTQuODUsMy41My03LjQ2YTE3My45MSwxNzMuOTEsMCwwLDAsNS44My0xNi42YzMuNDUtMTEuNTMsNi4yNC0yMy42Miw4Ljg4LTM1Ljg1czUtMjQuNjgsNy43My0zNy4zYTE3OS43OSwxNzkuNzksMCwwLDEsMy4zLDE5Yy4xOSwxLjYuMzksMy4yLjU2LDQuOGwuNDQsNC44MWMuMjksMy4yMS41LDYuNDMuNjUsOS42NS4wOSwxLjg0LjE1LDMuNjcuMiw1LjUxLDQuNzUtMS4yMyw5LjQtMi41OCwxMy45Mi00LjA3LDQyLjQyLTE0LDc0LjgxLTM5LjM1LDk2LjI3LTc1LjQ1LjMtLjYxLDEuMTItMS44NCwxLjQxLTIuNDlzLjU4LTEuMzIuODYtMmMuNTYtMS4zNywxLjEyLTIuNzYsMS42NS00LjE4czEuMDgtMi44NSwxLjU5LTQuM2MyLjA3LTUuNzcsNC0xMS42OSw1Ljc1LTE3LjY3czMuMzktMTIsNC44Mi0xOC4xMywyLjY3LTEyLjI5LDMuNjItMTguNTcsMS4zMiw2LjIxLDIuMzMsMTIuNTMsMy4xNnMxLjQ2LDEyLjc5LDEuOTIsMTkuMjMuNzYsMTIuOTIuODYsMTkuNDhjMCwxLjY0LDAsMy4yOSwwLDQuOTVzMCwzLjMzLS4wOCw1YzAsLjg0LS4wNiwxLjY5LS4xMSwyLjU2cy0uMDgsMS43Mi0uMTUsMi42M2wtLjA5LDkuNzRjMS42NSwxNS4xNiw0LjY3LDI0LjUyLDcuMzIsMzAsMS44LDMuNjgsNi43OCw0LjcxLDguNjgsMi41LDQuMy01LDEwLjY2LTE1LjM3LDE3LjMyLTM1LjA3Qzc5OCw5NDAuNDgsNzkwLjUsODY5LDc4Ny40NCw4NDYuNTRBMS40OSwxLjQ5LDAsMCwxLDc4Ny4yOSw4NDYuMTRaIi8+PHBhdGggY2xhc3M9ImNscy00IiBkPSJNNTIyLjI5LDk3LjQ5YTkzLjI1LDkzLjI1LDAsMCwxLDI5LjgxLDIuNTksODguNzEsODguNzEsMCwwLDEsMjUuNCwxMC43OCw3NS42NCw3NS42NCwwLDAsMSwxOS4yMSwxNyw2MS4yOCw2MS4yOCwwLDAsMSwxMS4xOCwyMS45LDU0LjEzLDU0LjEzLDAsMCwxLDEuOTEsMTUuMDgsNTEuODcsNTEuODcsMCwwLDEtMi4zMSwxNC40OCw1NSw1NSwwLDAsMS02LjI1LDEzLjQ3LDYxLjcsNjEuNywwLDAsMS0xMCwxMiwxMi4xNSwxMi4xNSwwLDAsMC0yLjMyLDMsMTMuOTEsMTMuOTEsMCwwLDAtMS40MSwzLjYyLDE2LjMxLDE2LjMxLDAsMCwwLS40NCw0LDE3LjgxLDE3LjgxLDAsMCwwLC41OSw0LjIzbDMuODgsMTQuNTlhMTguMjIsMTguMjIsMCwwLDEsLjU0LDYuMzksMTYuMzQsMTYuMzQsMCwwLDEtMS42Miw1Ljc4LDE0LjQ2LDE0LjQ2LDAsMCwxLTMuNTEsNC41NSwxMi44NywxMi44NywwLDAsMS01LjEyLDIuNjZsLTM2LjA2LDkuMjZhMTQuNTgsMTQuNTgsMCwwLDEtNi4zMy4yLDE2LjIzLDE2LjIzLDAsMCwxLTUuOS0yLjM4LDE4LjEsMTguMSwwLDAsMS00Ljc3LTQuNTYsMTguODYsMTguODYsMCwwLDEtMi45NC02LjMxbC00LTE1LjczYTE4LjE4LDE4LjE4LDAsMCwwLTQuNDEtOCwxNy44NSwxNy44NSwwLDAsMC0zLjUtMi44NywxNi45MSwxNi45MSwwLDAsMC00LjE2LTEuODYsODkuMjcsODkuMjcsMCwwLDEtMTguMTMtNy40OUE4MC4zNyw4MC4zNywwLDAsMSw0NzYsMjAyLjY4YTY4LjU3LDY4LjU3LDAsMCwxLTEyLTE0LjM2LDU5LjQ3LDU5LjQ3LDAsMCwxLTcuMjEtMTYuOTUsNTIuOTQsNTIuOTQsMCwwLDEsLjM2LTI3LjM1LDU3LDU3LDAsMCwxLDEzLjIxLTIzLjExLDcwLjUxLDcwLjUxLDAsMCwxLDIyLjc3LTE2LjE2QTg1Ljg3LDg1Ljg3LDAsMCwxLDUyMi4yOSw5Ny40OVoiLz48cGF0aCBjbGFzcz0iY2xzLTQiIGQ9Ik02NDcuMzUsMjE0LjRsMTAuMTMsMTMuNzdhMTQuNTEsMTQuNTEsMCwwLDEsMi43NSw4LjUyLDEyLjQ5LDEyLjQ5LDAsMCwxLS43MSw0LjIxLDkuODUsOS44NSwwLDAsMS0yLjEyLDMuNWwtMzAsMzEuMzNhMTQuNjQsMTQuNjQsMCwwLDAtMy43Myw3LjM1LDE4LjUyLDE4LjUyLDAsMCwwLC4zMiw4LjM0LDE3LjUzLDE3LjUzLDAsMCwwLDMuODYsNy4yNSwxMywxMywwLDAsMCw2LjgxLDQuMDdsMzguOSw4LjY1YTExLjI1LDExLjI1LDAsMCwxLDQuNSwyLjE5LDE1LDE1LDAsMCwxLDMuNDcsNCwxOCwxOCwwLDAsMSwyLjExLDUuMjUsMTkuMTQsMTkuMTQsMCwwLDEsLjQzLDYsMTcuNjQsMTcuNjQsMCwwLDEtLjg0LDQuMTYsMTUuMTYsMTUuMTYsMCwwLDEtMS42OSwzLjUzLDEzLDEzLDAsMCwxLTIuMzksMi43NCwxMC40NSwxMC40NSwwLDAsMS0yLjk1LDEuNzksOC4xNyw4LjE3LDAsMCwxLTEuMjcuNDEsOC42LDguNiwwLDAsMS0xLjMzLjIzLDguOTIsOC45MiwwLDAsMS0xLjM3LDAsOS42OSw5LjY5LDAsMCwxLTEuNDEtLjE3bC04My0xNS45YTEzLjExLDEzLjExLDAsMCwwLTEuNjQtLjIsMTIuNjUsMTIuNjUsMCwwLDAtMS42MywwLDEyLjM4LDEyLjM4LDAsMCwwLTEuNjIuMjIsMTIuNzUsMTIuNzUsMCwwLDAtMS41OC40MywxMy44MSwxMy44MSwwLDAsMC0xLjU0LjYzLDE0LjM0LDE0LjM0LDAsMCwwLTEuNDguODMsMTUuMTMsMTUuMTMsMCwwLDAtMS40LDEsMTQuOTEsMTQuOTEsMCwwLDAtMS4zLDEuMjJsLTc5LjE4LDgyLjczYy0uNDIuNDMtLjg1Ljg0LTEuMywxLjIyYTE2Ljc1LDE2Ljc1LDAsMCwxLTEuMzgsMS4wNWMtLjQ4LjMyLTEsLjYxLTEuNDUuODhzLTEsLjQ5LTEuNS43YTE0LjQ3LDE0LjQ3LDAsMCwxLTQsMSwxMy4xOCwxMy4xOCwwLDAsMS00LS4yMSwxMi41NCwxMi41NCwwLDAsMS0zLjctMS40MiwxMi43NCwxMi43NCwwLDAsMS0zLjE3LTIuNjRsLTIuMzYtMi43M2ExNy4yOCwxNy4yOCwwLDAsMS0zLjUxLTYuNDgsMjAuMjgsMjAuMjgsMCwwLDEtLjczLTcuNDJBMjIuMTIsMjIuMTIsMCwwLDEsNDc2LDM4Mi41OGw0MS42OC00MC45YTE4LjgyLDE4LjgyLDAsMCwwLDUuMS04LjgyLDE5LjUsMTkuNSwwLDAsMCwwLTkuNTQsMTgsMTgsMCwwLDAtNC40Ni04LjExLDE1Ljg0LDE1Ljg0LDAsMCwwLTguNDMtNC41MmwtNTcuNTUtMTFhMTQuMzksMTQuMzksMCwwLDEtNS40LTIuMjQsMTQuNjMsMTQuNjMsMCwwLDEtNi4xLTkuMzUsMTQuMzgsMTQuMzgsMCwwLDEsLjA5LTUuOTFsMS41OC03LjE5YTE0LjcsMTQuNywwLDAsMSwxLjUxLTQsMTQuODMsMTQuODMsMCwwLDEsOS41LTcuMTUsMTMuNzEsMTMuNzEsMCwwLDEsMS41OC0uMjcsMTQuMTcsMTQuMTcsMCwwLDEsMS42LS4xMSwxNSwxNSwwLDAsMSwxLjYzLjA4LDE2LDE2LDAsMCwxLDEuNjQuMjdsMTA0LjY1LDIzLjNhMTQsMTQsMCwwLDAsMS42OC4yNywxMy4zMSwxMy4zMSwwLDAsMCwxLjY3LjA1LDEyLjgzLDEyLjgzLDAsMCwwLDEuNjQtLjE2LDExLjE5LDExLjE5LDAsMCwwLDEuNi0uMzYsMTIuMjgsMTIuMjgsMCwwLDAsMS41NC0uNTUsMTQuNTMsMTQuNTMsMCwwLDAsMS40Ny0uNzUsMTIuODEsMTIuODEsMCwwLDAsMS4zOC0uOTMsMTUuMjIsMTUuMjIsMCwwLDAsMS4yOS0xLjEyWiIvPjxwYXRoIGNsYXNzPSJjbHMtMyIgZD0iTTk1MS41OCw2MTguOTFzLTMuNjMsMi41NC0xMCwyLjU0Yy0xMC45MiwwLTI5LjkxLTcuNDItNTIuNi00Ny42NWgwYy0zNy4zOC02OC4yMi03NS42Ny04Mi43Ny03Ny4zMy04My4zOGE0LjQ4LDQuNDgsMCwwLDAtMyw4LjQ0Yy4zOC4xNCwzOC44MiwxNC43NSw3NS41NSw4NC44N2wwLC4wOGMtNC45MSw4LjQtOS40OCwxMS4zMS05LjQ4LDExLjMxLDE1LjQ1LDI0LjA3LDU0Ljg3LDIwMi0yMjQuOTQsMjU3Ljg2LTUwLDEwLTkyLjM0LDE0LjM2LTEyOCwxNC4zNi0xNjMuNzcsMC0xODcuOTUtOTIuMjYtMTgyLjQzLTE1Ny44OGE0Nyw0NywwLDAsMC0xMS42Ni01LjY3YzQuNzItOC4yMywxMi4xMS0yMi4zLDIzLjMtNDYuMTMsNy4xLTE1LjE0LDEwLjE3LTMyLDkuMTMtNTBhNC41Miw0LjUyLDAsMCwwLTEuMzktMyw0LjQ2LDQuNDYsMCwwLDAtNy41MSwzLjUzYzEsMTYuNzgtMS43NCwzMS43Mi04LjI5LDQ1LjY3LTE1LjE4LDMyLjM2LTIzLjEyLDQ2LjE2LTI2LjY1LDUxLjY3bDAsMGMtMTkuMzksMjQuMS00NiwzOC4xMi01Ni40Myw0OGE4LjIsOC4yLDAsMCwxLTUuNjksMi40OGMtMTUuMjQsMC0zMS45LTQ3LjU3LDEzLjI0LTk0LjU3LDUxLTUzLjA3LDU1LjYyLTk4LjI5LDY5LjExLTExMS42Niw0LjI5LTQuMjUsMTIuMTMtNS43LDIwLjg0LTUuNywxOC43MywwLDQxLjQ1LDYuNjksNDEuNDUsNi42OUM0MjcuMTEsNTEyLDQ0OS42NCw1MTcuNSw1NjMsNDg5LjY4Yzc4LjgzLTE5LjM0LDEyNy4xNi0yMy4zMiwxNTMuNTktMjMuMzIsMTguNDYsMCwyNi4yMiwxLjk0LDI2LjIyLDEuOTRoMGMuMTgsMCwyLjY4LS41NywzNi43MS0yMS4xOCwxMS43NC03LjExLDIwLjEyLTEwLjkxLDI4LjU2LTEwLjkxLDE3LjQ4LDAsMzUuMTksMTYuMyw4My40MSw1My4yN0M5NjMsNTQ0LjMsOTUxLjU4LDYxOC45MSw5NTEuNTgsNjE4LjkxWiIvPjxwYXRoIGNsYXNzPSJjbHMtMSIgZD0iTTgzMi40Nyw2MjQuODdzNTItOTctNTIuODctMTIxLjE2cy0xMzMuNDgsNDcuNC0xMTkuOTIsOTEuNjhjMCwwLTQ2LTEuNDEtNTUuNDcsMTMuNzEsMCwwLTMxLjQ2LTEwMy45Mi0xNjctMzEuODFDMzU3LjM0LDYxOS43OSwzODQuOTQsNzAwLjYsNDE5LDcxOC45Miw0MjMuODcsNzIxLjU0LDQyNi44Nyw3MjguNDEsNDIxLjcsNzM5YTU2LjIsNTYuMiwwLDAsMC01LjE0LDMyLjQ4YzQuMTQsMzEsMzMuNDgsNDQuNjQsMTA5LjI2LDM0LjMxLDcuMzEtMSwxNC4zNy0yLjI5LDIxLjE5LTMuOGwxLjU4LS4zN3EyLjQ5LS41Nyw0Ljk0LTEuMThhMjUzLjE2LDI1My4xNiwwLDAsMCwxMTgtNjcuMzJjMy45My04LjEzLDQuNDItMjIuNS43NS0zMi40MS02LjU2LTE3LjY5LTI0Ljk0LTI2LjE1LTI1LjEzLTI2LjIzbDAtLjA4Yy04LjUyLTQuNS0xOC40My03LjcyLTI1LjUyLTMuODgtMTMuMjMsNy4xNi0yMy42NywxNi4yMy0yNS41NSwxLjQ0LS44OC02LjkzLDEuMjktNDEuOTQsNDIuOTItNTMuMzZzNTkuNzUsOC4yLDYyLDE4LjM1YzEuNTQsNi44Ny0yLjE5LDIwLjY0LTExLjg3LDIxLjE2LTUuMjUuMjgtNy4yNyw0LjYtOS4xMSw5Ljc3YTguNjcsOC42NywwLDAsMCwxLDgsNjEuNTgsNjEuNTgsMCwwLDEsMTAuMzEsMTcuNzNjNC44OSwxMy4xOSw0Ljg2LDI3LjUxLDAsNDIuNjhhMTU2LjkxLDE1Ni45MSwwLDAsMCw4MS4zMSw2LjExbDEuOTMtLjM4Yy44OC0uMTgsMS43Ni0uMzYsMi42NC0uNTZhMTY3LDE2NywwLDAsMCwzMS44My0xMC40NEM4NzIsNzAzLjI4LDg0MS40MSw2MzEuNzMsODMyLjQ3LDYyNC44N1oiLz48cGF0aCBjbGFzcz0iY2xzLTEiIGQ9Ik03NDMuNDksNzY4LjQ2QTE4MC41MywxODAuNTMsMCwwLDEsNjgwLjM5LDc1N2EyNzguNTEsMjc4LjUxLDAsMCwxLTM4LjYsMzAuMSwyNzQuOTMsMjc0LjkzLDAsMCwxLTcwLjIyLDMyLjQ4YzE2LjksMTEuMzcsNDguNzYsMjAuNDYsMTA2LjI5LDMuMTUsNTUuODEtMTYuNzksNzguNjktMzksODcuOTQtNTUuNzFBMTc5Ljg5LDE3OS44OSwwLDAsMSw3NDMuNDksNzY4LjQ2WiIvPjxwYXRoIGNsYXNzPSJjbHMtNCIgZD0iTTU3MS4xNiw2MDkuNzJDNTYxLjM3LDU4NC42NSw1MzAuMjIsNTcyLjUzLDQ5Niw1NzhhNTcuNjMsNTcuNjMsMCwxLDEtNjUuNDUsMzYuMjZjLTE0LjQ4LDE3LjQ4LTIwLjEzLDM4LjI4LTEzLjA3LDU2LjM3LDEyLDMwLjc0LDU2LjEyLDQyLDk4LjU0LDI1LjE5UzU4My4xNiw2NDAuNDYsNTcxLjE2LDYwOS43MloiLz48cGF0aCBjbGFzcz0iY2xzLTQiIGQ9Ik03NzYsNjEyLjUyYTUwLjUsMTAsMCwwLDEtMzEuMTItOTAuMjhjLTI4LjUxLDIuNTQtNTEuMjIsMjAuNzgtNTMuMTUsNDQuNjgtMi4yMywyNy41LDIzLjg4LDUyLjA1LDU4LjMxLDU0Ljg0LDIwLjg5LDEuNyw0MC01LDUyLjM3LTE2LjY5QTUwLjMyLDUwLjMyLDAsMCwxLDc3Niw2MTIuNTJaIi8+PHBhdGggY2xhc3M9ImNscy0xIiBkPSJNMTMxLjY5LDEyMzMuNTNMMTI1LDEyNjkuMmwtNi4xLDIuNDRhOTguNTMsOTguNTMsMCwwLDAtMjEuNDktMTEuNTlxLTExLjEzLTQuMjYtMjAuMjgtNC4yN3EtMTIuMTksMC0xOS41MSw2LjU2dC03LjMxLDE1LjA5cTAsOC44NSw4LjA3LDE0Ljk0dDI1LjQ2LDE0LjMzYTI0Mi44MSwyNDIuODEsMCwwLDEsMjcuMjksMTQuMTcsNjEuNiw2MS42LDAsMCwxLDE4LDE3LjIzcTcuNDcsMTAuNjcsNy40NywyNi4yMmE1NC40OSw1NC40OSwwLDAsMS05LjE0LDMwLjYzcS05LjE1LDEzLjg5LTI1LjkyLDIyVDYyLjc4LDE0MjVxLTI5LDAtNTguMjMtMTIuNDlsNS44LTM4LjQyLDQuNTctMi40NGE4OS42Miw4OS42MiwwLDAsMCwyNi42OCwxNi4zMXExNC40OCw1LjY1LDI1Ljc2LDUuNjRxMTMuNDEsMCwyMC44OC02LjU1dDcuNDctMTUuN2ExOSwxOSwwLDAsMC04LjA4LTE1Ljg2cS04LjA5LTYuMDktMjYuMDYtMTQuNjNhMjI4LjM1LDIyOC4zNSwwLDAsMS0yNi44My0xMy43Miw1OC43Myw1OC43MywwLDAsMS0xNy42OS0xNy4wN3EtNy4zMS0xMC42Ni03LjMxLTI1LjkyYTU1LDU1LDAsMCwxLDkuMTQtMzAuOTRxOS4xNS0xMy44NywyNS42MS0yMS44dDM3LjUtNy45MkExMzAuNzksMTMwLjc5LDAsMCwxLDEzMS42OSwxMjMzLjUzWiIvPjxwYXRoIGNsYXNzPSJjbHMtMSIgZD0iTTIwMy4zMywxMzU5Ljc0bDIuMTMsNjIuNUgxNjQuOTFsMi4xNC01OC44NC0xLjgzLTE1Mi4xMyw0MC41NS0zWm00MS4xNS0xNS4yNHExNi40NywyNi41Miw0OS4zOSw3MWwtLjMsNC4yN2EyMDUuNTksMjA1LjU5LDAsMCwxLTIyLjcyLDMuODFsLTE0Ljc4LDEuNjgtNC4yNy0xLjgzYTY0Mi4yOSw2NDIuMjksMCwwLDEtNDYuMzQtNzUuM3YtMi43NWwzNS4zNy01MC4zLDcuMzEtMTQuNjNoNDIuNjhaIi8+PHBhdGggY2xhc3M9ImNscy0xIiBkPSJNNDUwLDEzOTUuNzJsLTMuNjUsMjEuMzRxLTExLjMsNy4zMi0yMy4xNyw3LjYyYTI3LjUxLDI3LjUxLDAsMCwxLTE0LjY0LTdxLTUuNzktNS40OS04Ljg0LTE1Ljg2aC0yLjc0cS0xNy4zOSwxNy4wOS0zNiwyMi4yNi0yMy4xOCwwLTM1LjIxLTEwLjUyVDMxNCwxMzgzLjIybC42MS0zNi0xLjUyLTY0LDM5LjMzLTMuMzUtLjkyLDg5LjkzcS0uMywxMC42OCw0LjI3LDE2LjE2dDEzLjcyLDUuNDlxMTMuNDEsMCwyNi41Mi0xMS44OXYtOTYuMzRsMzguNzItMy4zNUw0MzIsMTM4NS4zNWMwLDMuMjYuNTUsNS41OSwxLjY3LDdzMi45LDIuMTQsNS4zNCwyLjE0YTM1LjE3LDM1LjE3LDAsMCwwLDguMjMtMS4yMloiLz48cGF0aCBjbGFzcz0iY2xzLTEiIGQ9Ik01ODkuNTksMTI5Ni42M3ExNC4zMiwxOCwxNC4zMyw1MC45MnEwLDM3LjItMTguNDUsNTcuNDd0LTUyLDIwLjI3YTEyMC44NSwxMjAuODUsMCwwLDEtMjAuNDItMS44M2wuOTEsNTUuMThINDczLjc0bDIuMTMtMTE0LjkzTDQ3NCwxMjgzLjIybDM4LjcyLTMuMzUtLjMsMjAuNzNoMi4xM2ExMDUuMTUsMTA1LjE1LDAsMCwxLDE2LjQ3LTEzLjI2LDk0Ljc0LDk0Ljc0LDAsMCwxLDE3LjY4LTguNjlRNTc1LjI2LDEyNzguNjUsNTg5LjU5LDEyOTYuNjNabS0zMS43MSw5MC44NnE4LjI0LTExLjI4LDguMjQtMzMuMjRxMC0yMS4zMy02Ljg2LTMyLjE2VDUzOSwxMzExLjI3cS0xMy4xMSwwLTI2LjUyLDEzLjExbC0uMzEsMzUuMzYuNjEsMzQuNDVhNTQuNjUsNTQuNjUsMCwwLDAsMjEsNC41OFE1NDkuNjQsMTM5OC43Nyw1NTcuODgsMTM4Ny40OVoiLz48cGF0aCBjbGFzcz0iY2xzLTEiIGQ9Ik03NDcuNTEsMTI5Ni42M3ExNC4zMiwxOCwxNC4zMyw1MC45MnEwLDM3LjItMTguNDUsNTcuNDd0LTUyLDIwLjI3YTEyMC44NSwxMjAuODUsMCwwLDEtMjAuNDItMS44M2wuOTEsNTUuMThINjMxLjY2bDIuMTMtMTE0LjkzTDYzMiwxMjgzLjIybDM4LjcyLTMuMzUtLjMsMjAuNzNoMi4xM0ExMDUuNTcsMTA1LjU3LDAsMCwxLDY4OSwxMjg3LjM0YTk1LjE0LDk1LjE0LDAsMCwxLDE3LjY5LTguNjlRNzMzLjE4LDEyNzguNjUsNzQ3LjUxLDEyOTYuNjNabS0zMS43MSw5MC44NnE4LjI0LTExLjI4LDguMjMtMzMuMjRxMC0yMS4zMy02Ljg1LTMyLjE2dC0yMC4yOC0xMC44MnEtMTMuMTEsMC0yNi41MiwxMy4xMWwtLjMxLDM1LjM2LjYxLDM0LjQ1YTU0LjY1LDU0LjY1LDAsMCwwLDIxLDQuNThRNzA3LjU2LDEzOTguNzcsNzE1LjgsMTM4Ny40OVoiLz48cGF0aCBjbGFzcz0iY2xzLTEiIGQ9Ik04OTkuMzMsMTM1Ni4zOUw4MTcsMTM1N3EyLjc1LDM4LjEyLDM4LjcyLDM4LjExcTE4LjksMCw0Mi4wNy0xMC42N2wzLjM1LDIuMTMtNi4xLDMwLjE4cS0yMy4xNiw4LjU0LTQzLjU5LDguNTQtMzMuNTQsMC01Mi41OS0xOS41MXQtMTkuMDYtNTRxMC0zNC4xNCwxOC42LTU0LjEydDUwLjMtMjBxMjcuMTMsMCw0MS45MiwxNC43OXQxNC43OSw0MS4zMWExMjguODIsMTI4LjgyLDAsMCwxLTEuNTMsMTcuNjhabS0yOS4yNy0yNy4xM3EwLTEyLjE5LTUuNDgtMTguNDV0LTE2LjE2LTYuMjVxLTExLjg5LDAtMTkuODIsNy43OHQtMTAuNjcsMjIuNGw1MS41Mi0xLjIyWiIvPjxwYXRoIGNsYXNzPSJjbHMtMSIgZD0iTTEwMTkuNDUsMTI4MC43OHYzNy41bC00LjI3LDEuNTJhMjkuNjEsMjkuNjEsMCwwLDAtMTEuMjgtMi4xM3EtMTcuNjgsMC0zMiwyMi44N3YxOS4ybDIuMTMsNjIuNUg5MzMuNDdsMi40NC01OC41My0xLjgzLTgwLjQ5LDM4LjQyLTMuMzUtLjMxLDI3Ljc0aDIuNDRxMTQuOTQtMjcuNDMsMzcuMTktMjcuNDRBNjcuMjQsNjcuMjQsMCwwLDEsMTAxOS40NSwxMjgwLjc4WiIvPjwvc3ZnPg==" class="skupper-logo" alt="Skupper">
            <h1>Getback Dashboard</h1>
        </div>
        <p class="subtitle">
            Test your backend service distribution with Skupper.
            <span class="status" id="status">● LIVE</span>
        </p>


        <div class="config-and-controls">
            <div class="config">
                <h2>Backend Configuration</h2>
                <div class="config-row">
                    <label>HTTP Backend:</label>
                    <input type="text" id="http-backend" placeholder="hostname:9091">
                    <span></span>
                </div>
                <div class="config-row">
                    <label>TCP Backend:</label>
                    <input type="text" id="tcp-backend" placeholder="hostname:9092">
                    <span></span>
                </div>
                <div class="config-row">
                    <label>Amount:</label>
                    <input type="number" id="amount" min="1" max="100" value="10" style="width: 100px;">
                    <span style="color: #666; font-size: 0.85rem;">requests per click</span>
                </div>
                <div class="config-row">
                    <label></label>
                    <button onclick="saveConfig()">Save</button>
                    <span></span>
                </div>
                <p style="color: #666; font-size: 0.85rem; margin-top: 8px;">
                    Examples: <code>getback:9091</code>, <code>backend-canary:9092</code>, <code>localhost:9091</code>
                </p>
            </div>

            <div class="controls">
                <h2>Make Requests</h2>
                <div class="button-group">
                    <label>HTTP:</label>
                    <button class="http" onclick="makeRequest('http')">Send HTTP Requests</button>
                </div>
                <div class="button-group">
                    <label>TCP:</label>
                    <button class="tcp" onclick="makeRequest('tcp', 'test')">Pulse</button>
                    <button class="tcp secondary" onclick="makeRequest('tcp', '2')">Linger (2s)</button>
                    <button class="tcp secondary" onclick="makeRequest('tcp', 'OPEN')">Hold open</button>
                    <button class="tcp secondary" onclick="cycleConnections()">Cycle</button>
                </div>
                <div class="button-group">
                    <label>Connections:</label>
                    <button class="danger" onclick="closeAllConnections()">Close All</button>
                </div>
            </div>
        </div>

        <div class="distribution">
            <h2>Request Distribution <button onclick="clearDistribution()" style="float: right; padding: 4px 12px; font-size: 0.8rem;">Clear</button></h2>
            <div id="distribution">
                <p style="color: #888; text-align: center;">No requests yet</p>
            </div>
        </div>

        <div class="history">
            <h2>Request History (Last 20) <button onclick="clearHistory()" style="float: right; padding: 4px 12px; font-size: 0.8rem;">Clear</button></h2>
            <div id="history">
                <p style="color: #888; text-align: center;">No requests yet</p>
            </div>
        </div>

        <div class="footer">
            getback v1.0.0
        </div>
    </div>

    <script>
        // Default backend from server configuration
        const DEFAULT_BACKEND_HOST = '__BACKEND_HOST__';

        // State for history and distribution (load from localStorage)
        let requestHistory = [];
        let serverCounts = {};

        // Load persisted state from localStorage
        try {
            const savedHistory = localStorage.getItem('requestHistory');
            const savedCounts = localStorage.getItem('serverCounts');
            if (savedHistory) requestHistory = JSON.parse(savedHistory);
            if (savedCounts) serverCounts = JSON.parse(savedCounts);
        } catch (e) {
            console.error('Failed to load state:', e);
        }

        // Save state to localStorage
        function saveState() {
            localStorage.setItem('requestHistory', JSON.stringify(requestHistory));
            localStorage.setItem('serverCounts', JSON.stringify(serverCounts));
        }

        // Initialize UI from localStorage on page load
        function initConfig() {
            const httpBackend = localStorage.getItem('httpBackend') || `${DEFAULT_BACKEND_HOST}:9091`;
            const tcpBackend = localStorage.getItem('tcpBackend') || `${DEFAULT_BACKEND_HOST}:9092`;
            const amount = parseInt(localStorage.getItem('amount') || '10');
            document.getElementById('http-backend').value = httpBackend;
            document.getElementById('tcp-backend').value = tcpBackend;
            document.getElementById('amount').value = amount;

            // Update UI with persisted state
            updateHistory();
            updateDistribution();
        }

        // Toast notification system
        function showToast(title, message, type = 'info') {
            const container = document.getElementById('toast-container');
            const toast = document.createElement('div');
            toast.className = `toast ${type}`;
            toast.innerHTML = `
                <div class="toast-title">${title}</div>
                <div class="toast-message">${message}</div>
            `;
            container.appendChild(toast);

            setTimeout(() => {
                toast.style.animation = 'slideIn 0.3s ease-out reverse';
                setTimeout(() => toast.remove(), 300);
            }, 3000);
        }

        // Read current configuration from input fields
        function getConfig() {
            return {
                httpBackend: document.getElementById('http-backend').value,
                tcpBackend: document.getElementById('tcp-backend').value,
                amount: parseInt(document.getElementById('amount').value) || 10
            };
        }

        // Save backend configuration to localStorage
        function saveConfig() {
            const config = getConfig();
            localStorage.setItem('httpBackend', config.httpBackend);
            localStorage.setItem('tcpBackend', config.tcpBackend);
            localStorage.setItem('amount', config.amount);
            showToast('Configuration Saved', `Backend: ${config.httpBackend}, Amount: ${config.amount}`, 'success');
        }

        // Initialize configuration on page load
        initConfig();

        // Timeout wrapper for fetch
        async function fetchWithTimeout(url, options, timeoutMs = 10000) {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

            try {
                const response = await fetch(url, {
                    ...options,
                    signal: controller.signal
                });
                clearTimeout(timeoutId);
                return response;
            } catch (error) {
                clearTimeout(timeoutId);
                if (error.name === 'AbortError') {
                    throw new Error('Request timeout - check backend connectivity');
                }
                throw error;
            }
        }

        async function makeRequest(protocol, command = null) {
            const config = getConfig();
            const backend = protocol === 'http' ? config.httpBackend : config.tcpBackend;
            const amount = config.amount;

            // Disable all buttons
            const buttons = document.querySelectorAll('button');
            buttons.forEach(btn => btn.disabled = true);

            const startTime = performance.now();

            try {
                // Send single request to server with amount parameter (server-side batching)
                const url = protocol === 'http' ? '/api/request/http' : '/api/request/tcp';
                const bodyData = protocol === 'tcp'
                    ? { command: command || 'test', backend, amount }
                    : { backend, amount };

                const response = await fetchWithTimeout(url, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(bodyData)
                }, 30000);  // 30 second timeout for large batches

                const data = await response.json();
                const results = data.results || [];
                const totalTime = Math.round(performance.now() - startTime);

                // Calculate stats
                const servers = new Set(results.map(r => r.server));
                const avgLatency = results.length > 0
                    ? Math.round(results.reduce((sum, r) => sum + r.latency_ms, 0) / results.length)
                    : 0;

                // Process all results
                results.forEach(result => {
                    // Add to history (keep last 20)
                    const entry = {
                        protocol,
                        counter: result.counter,
                        server: result.server,
                        latency: result.latency_ms,
                        command: result.command,
                        timestamp: new Date().toLocaleTimeString()
                    };
                    requestHistory.unshift(entry);
                    if (requestHistory.length > 20) requestHistory.pop();

                    // Update server counts
                    serverCounts[result.server] = (serverCounts[result.server] || 0) + 1;
                });

                // Update UI once after all requests complete
                updateHistory();
                updateDistribution();

                // Persist state to localStorage
                saveState();

                // Show success toast
                if (amount > 1) {
                    const protocolLabel = protocol.toUpperCase();
                    const successRate = data.successful === amount ? '' : ` (${data.successful}/${amount} succeeded)`;
                    showToast(
                        `${amount} ${protocolLabel} requests completed${successRate}`,
                        `${servers.size} servers • ${avgLatency}ms avg`,
                        'success'
                    );
                }

            } catch (error) {
                console.error('Request failed:', error);
                showToast('Request Failed', error.message || 'Backend unavailable', 'error');
            } finally {
                // Re-enable all buttons
                buttons.forEach(btn => btn.disabled = false);
            }
        }

        function updateHistory() {
            const historyEl = document.getElementById('history');
            if (requestHistory.length === 0) {
                historyEl.innerHTML = '<p style="color: #888; text-align: center;">No requests yet</p>';
                return;
            }

            historyEl.innerHTML = requestHistory.map(entry => {
                const details = entry.protocol === 'tcp' && entry.command
                    ? `Counter: ${entry.counter} | Command: ${entry.command}`
                    : `Counter: ${entry.counter}`;

                return `
                    <div class="history-entry">
                        <span class="time">${entry.timestamp}</span>
                        <span>
                            <span class="protocol ${entry.protocol}">${entry.protocol.toUpperCase()}</span>
                            <span class="details">${details}</span>
                            <span class="server">${entry.server}</span>
                        </span>
                        <span class="latency">${entry.latency}ms</span>
                    </div>
                `;
            }).join('');
        }

        function updateDistribution() {
            const distEl = document.getElementById('distribution');
            const servers = Object.keys(serverCounts);

            if (servers.length === 0) {
                distEl.innerHTML = '<p style="color: #888; text-align: center;">No requests yet</p>';
                return;
            }

            const total = Object.values(serverCounts).reduce((a, b) => a + b, 0);
            const entries = servers.map(server => {
                const count = serverCounts[server];
                const percent = Math.round((count / total) * 100);
                return { server, count, percent };
            }).sort((a, b) => b.count - a.count);

            distEl.innerHTML = entries.map(e => `
                <div class="dist-entry">
                    <span class="server">${e.server}</span>
                    <span class="count">${e.count} requests</span>
                    <span class="percent">(${e.percent}%)</span>
                </div>
            `).join('') + `
                <div class="dist-entry">
                    <span>Total</span>
                    <span class="count">${total} requests</span>
                    <span></span>
                </div>
            `;
        }

        // Confirmation state tracking
        let pendingClear = null;

        // Clear distribution data with confirmation
        function clearDistribution() {
            const btn = event.target;

            if (pendingClear === 'distribution') {
                // Second click - actually clear
                const count = Object.values(serverCounts).reduce((a, b) => a + b, 0);
                serverCounts = {};
                updateDistribution();
                saveState();
                showToast('Distribution Cleared', `Reset ${count} request records`, 'info');
                btn.textContent = 'Clear';
                pendingClear = null;
            } else {
                // First click - ask for confirmation
                pendingClear = 'distribution';
                btn.textContent = 'Click again to confirm';
                btn.style.background = '#f44336';
                setTimeout(() => {
                    if (pendingClear === 'distribution') {
                        btn.textContent = 'Clear';
                        btn.style.background = '';
                        pendingClear = null;
                    }
                }, 3000);
            }
        }

        // Clear history data with confirmation
        function clearHistory() {
            const btn = event.target;

            if (pendingClear === 'history') {
                // Second click - actually clear
                const count = requestHistory.length;
                requestHistory = [];
                updateHistory();
                saveState();
                showToast('History Cleared', `Removed ${count} entries`, 'info');
                btn.textContent = 'Clear';
                pendingClear = null;
            } else {
                // First click - ask for confirmation
                pendingClear = 'history';
                btn.textContent = 'Click again to confirm';
                btn.style.background = '#f44336';
                setTimeout(() => {
                    if (pendingClear === 'history') {
                        btn.textContent = 'Clear';
                        btn.style.background = '';
                        pendingClear = null;
                    }
                }, 3000);
            }
        }

        // Close all persistent TCP connections
        async function closeAllConnections() {
            const btn = event.target;

            if (pendingClear === 'connections') {
                // Second click - actually close
                try {
                    btn.disabled = true;
                    btn.textContent = 'Closing...';

                    const response = await fetchWithTimeout('/api/connections/close-all', {
                        method: 'POST'
                    }, 5000);

                    const data = await response.json();

                    // Re-enable Cycle button if it was cycling
                    const cycleBtn = Array.from(document.querySelectorAll('button')).find(b => b.textContent === 'Cycling...');
                    if (cycleBtn) {
                        cycleBtn.textContent = 'Cycle';
                        cycleBtn.disabled = false;
                    }

                    const message = data.cycling_stopped
                        ? `Stopped cycling and closed ${data.closed} connections`
                        : `Closed ${data.closed} persistent TCP connections`;
                    showToast('Connections Closed', message, 'success');
                } catch (err) {
                    showToast('Error', `Failed to close connections: ${err.message}`, 'error');
                } finally {
                    btn.textContent = 'Close All';
                    btn.disabled = false;
                    pendingClear = null;
                }
            } else {
                // First click - ask for confirmation
                pendingClear = 'connections';
                btn.textContent = 'Click again to confirm';
                btn.style.background = '#f44336';
                setTimeout(() => {
                    if (pendingClear === 'connections') {
                        btn.textContent = 'Close All';
                        btn.style.background = '';
                        pendingClear = null;
                    }
                }, 3000);
            }
        }

        // Cycle connections: ramp up over 20s, ramp down over 20s, repeat continuously
        async function cycleConnections() {
            const config = getConfig();
            const backend = config.protocol === 'http' ? config.httpBackend : config.tcpBackend;
            const amount = config.amount;

            if (!backend) {
                showToast('Error', 'Please configure TCP backend first', 'error');
                return;
            }

            const btn = event.target;

            try {
                btn.disabled = true;
                btn.textContent = 'Cycling...';

                const response = await fetchWithTimeout('/api/connections/cycle', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ backend, amount })
                }, 5000);

                const data = await response.json();
                showToast('Cycling Started', `Ramping to ${amount} connections (40s/cycle). Press "Close All" to stop.`, 'success');

            } catch (err) {
                showToast('Error', `Failed to start cycle: ${err.message}`, 'error');
                btn.textContent = 'Cycle';
                btn.disabled = false;
            }
        }
    </script>
</body>
</html>
"""
    return html.replace('__BACKEND_HOST__', backend_host)


def parse_backend(backend: str, default_host: str = 'localhost', default_port: int = 9091) -> tuple[str, int]:
    """Parse backend string in 'host:port' format.

    Args:
        backend: Backend string (e.g., 'getback:9091', 'localhost:9092')
        default_host: Default host if parsing fails
        default_port: Default port if parsing fails

    Returns:
        Tuple of (host, port)
    """
    if not backend or not backend.strip():
        return (default_host, default_port)

    try:
        if ':' in backend:
            host, port_str = backend.rsplit(':', 1)
            # Skip if port string is empty or whitespace
            if not port_str.strip():
                return (default_host, default_port)
            port = int(port_str.strip())
            if 1 <= port <= 65535 and host.strip():
                return (host.strip(), port)
    except (ValueError, AttributeError):
        pass

    return (default_host, default_port)


def compute_latency_percentile(latencies: list, percentile: float) -> int:
    """Compute percentile from latency list.

    Args:
        latencies: Sorted list of latency values
        percentile: Percentile to compute (0-100)

    Returns:
        Latency value at percentile (in ms)
    """
    if not latencies:
        return 0
    idx = int(len(latencies) * (percentile / 100))
    idx = min(idx, len(latencies) - 1)
    return latencies[idx]


def format_stats_json(
    http_counter: Counter,
    tcp_counter: Counter,
    start_time: float,
    latency_stats: Dict[str, list],
    active_tcp_connections: set
) -> str:
    """Format stats as JSON with latency aggregates.

    Args:
        http_counter: HTTP counter instance
        tcp_counter: TCP counter instance
        start_time: Server start timestamp
        latency_stats: Latency tracking dict ({"http": [...], "tcp": [...]})
        active_tcp_connections: Set of active persistent TCP connections

    Returns:
        JSON string with current stats and latency aggregates
    """
    # Compute HTTP latency stats
    http_latencies = sorted(latency_stats.get("http", []))
    http_latency = {}
    if http_latencies:
        http_latency = {
            "min": min(http_latencies),
            "max": max(http_latencies),
            "avg": int(sum(http_latencies) / len(http_latencies)),
            "p50": compute_latency_percentile(http_latencies, 50),
            "p95": compute_latency_percentile(http_latencies, 95),
            "p99": compute_latency_percentile(http_latencies, 99),
            "count": len(http_latencies)
        }

    # Compute TCP latency stats
    tcp_latencies = sorted(latency_stats.get("tcp", []))
    tcp_latency = {}
    if tcp_latencies:
        tcp_latency = {
            "min": min(tcp_latencies),
            "max": max(tcp_latencies),
            "avg": int(sum(tcp_latencies) / len(tcp_latencies)),
            "p50": compute_latency_percentile(tcp_latencies, 50),
            "p95": compute_latency_percentile(tcp_latencies, 95),
            "p99": compute_latency_percentile(tcp_latencies, 99),
            "count": len(tcp_latencies)
        }

    stats = {
        "http_counter": http_counter._value,
        "tcp_counter": tcp_counter._value,
        "active_tcp_connections": len(active_tcp_connections),
        "uptime": int(time.time() - start_time),
        "timestamp": int(time.time()),
        "latency": {
            "http": http_latency,
            "tcp": tcp_latency
        }
    }
    return json.dumps(stats)


async def make_http_request(backend_host: str = 'localhost', backend_port: int = 9091) -> Dict[str, Any]:
    """Make HTTP request to backend server.

    Args:
        backend_host: Backend host to connect to (default: localhost)
        backend_port: Backend port to connect to (default: 9091)

    Returns:
        Dict with counter, server, latency_ms, timestamp
    """
    start = time.time()
    reader, writer = await asyncio.open_connection(backend_host, backend_port)

    try:
        # Send HTTP request
        request = b"GET / HTTP/1.0\r\n\r\n"
        writer.write(request)
        await writer.drain()

        # Read response
        response = await reader.read(1024)
        response_text = response.decode('utf-8')

        # Parse response body (skip headers)
        body = response_text.split('\r\n\r\n', 1)[1].strip() if '\r\n\r\n' in response_text else ""

        # Parse "N (server_id)" format
        if not body:
            raise ValueError("Empty response from backend")

        parts = body.split(' (', 1)
        if not parts[0].strip():
            raise ValueError(f"Invalid response format: '{body}'")

        counter = int(parts[0].strip())
        server = parts[1].rstrip(')') if len(parts) > 1 else "unknown"

        latency_ms = int((time.time() - start) * 1000)

        return {
            "counter": counter,
            "server": server,
            "latency_ms": latency_ms,
            "timestamp": int(time.time())
        }
    finally:
        writer.close()
        await writer.wait_closed()


async def make_tcp_request(
    command: str = "test",
    backend_host: str = 'localhost',
    backend_port: int = 9092,
    active_tcp_connections: set = None
) -> Dict[str, Any]:
    """Make TCP request to backend server.

    Args:
        command: TCP command to send
        backend_host: Backend host to connect to (default: localhost)
        backend_port: Backend port to connect to (default: 9092)
        active_tcp_connections: Set to track persistent connections (optional)

    Returns:
        Dict with counter, server, latency_ms, command, timestamp
    """
    start = time.time()
    reader, writer = await asyncio.open_connection(backend_host, backend_port)

    try:
        # Send TCP command
        writer.write(f"{command}\n".encode('utf-8'))
        await writer.drain()

        # Read response
        response = await reader.readline()
        response_text = response.decode('utf-8').strip()

        # Parse "N (server_id)" format
        if not response_text:
            raise ValueError("Empty response from backend")

        parts = response_text.split(' (', 1)
        if not parts[0].strip():
            raise ValueError(f"Invalid response format: '{response_text}'")

        counter = int(parts[0].strip())
        server = parts[1].rstrip(')') if len(parts) > 1 else "unknown"

        latency_ms = int((time.time() - start) * 1000)

        # For OPEN command, keep connection alive
        if command == "OPEN" and active_tcp_connections is not None:
            active_tcp_connections.add(writer)
            logger.debug(f"Persistent connection opened to {backend_host}:{backend_port} (total: {len(active_tcp_connections)})")

        return {
            "counter": counter,
            "server": server,
            "latency_ms": latency_ms,
            "command": command,
            "timestamp": int(time.time())
        }
    finally:
        # Only close non-persistent connections
        if command != "OPEN":
            writer.close()
            await writer.wait_closed()


async def dashboard_handler(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    http_counter: Counter,
    tcp_counter: Counter,
    start_time: float,
    backend_host: str,
    distribution_counts: Dict[str, int],
    latency_stats: Dict[str, list],
    active_tcp_connections: set,
    cycling_active: dict,
    current_cycle_task: dict
) -> None:
    """Handle dashboard HTTP requests.

    Args:
        reader: Async stream reader
        writer: Async stream writer
        http_counter: HTTP counter instance
        tcp_counter: TCP counter instance
        start_time: Server start timestamp
        backend_host: Backend host for making requests
        distribution_counts: Server-side distribution tracking dict
        latency_stats: Server-side latency tracking dict ({"http": [...], "tcp": [...]})
        active_tcp_connections: Set of active persistent TCP connections (dashboard → backends)
        cycling_active: Dict with 'active' key tracking if cycling is running
        current_cycle_task: Dict with 'task' key holding current cycle task
    """
    addr = writer.get_extra_info('peername')
    logger.debug(f"Dashboard request from {addr}")

    try:
        # Read HTTP request headers
        data = await reader.readuntil(b'\r\n\r\n')
        request_text = data.decode('utf-8')
        request_line = request_text.split('\r\n')[0]
        parts = request_line.split(' ')
        method = parts[0] if len(parts) >= 1 else "GET"
        path = parts[1] if len(parts) >= 2 else "/"
        logger.debug(f"Request: {method} {path}")

        # Parse Content-Length for POST requests
        content_length = 0
        for line in request_text.split('\r\n')[1:]:
            if line.lower().startswith('content-length:'):
                try:
                    content_length_str = line.split(':', 1)[1].strip()
                    if content_length_str:
                        content_length = int(content_length_str)
                except (ValueError, IndexError):
                    logger.warning(f"Invalid Content-Length header: {line}")
                break

        # Read request body if present
        request_body = ""
        if content_length > 0:
            body_data = await reader.readexactly(content_length)
            request_body = body_data.decode('utf-8')

        if path == "/api/request/http" and method == "POST":
            # Make HTTP request(s) to backend (server-side batching)
            # Parse backend and amount from request body
            req_backend = backend_host
            req_port = 9091
            amount = 1
            if request_body:
                try:
                    body_json = json.loads(request_body)
                    if 'backend' in body_json:
                        req_backend, req_port = parse_backend(body_json['backend'], backend_host, 9091)
                    amount = body_json.get('amount', 1)
                except json.JSONDecodeError:
                    pass

            # Make N concurrent requests to backend
            tasks = [make_http_request(req_backend, req_port) for _ in range(amount)]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Filter out exceptions and track successful requests
            successful_results = []
            for result in results:
                if isinstance(result, dict):
                    successful_results.append(result)
                    # Track distribution server-side
                    server = result.get('server', 'unknown')
                    distribution_counts[server] = distribution_counts.get(server, 0) + 1
                    # Track latency (keep last 1000)
                    latency_stats["http"].append(result.get('latency_ms', 0))
                    if len(latency_stats["http"]) > 1000:
                        latency_stats["http"].pop(0)

            body = json.dumps({"results": successful_results, "total": amount, "successful": len(successful_results)})
            response = (
                "HTTP/1.0 200 OK\r\n"
                "Content-Type: application/json\r\n"
                "\r\n"
                f"{body}\n"
            ).encode('utf-8')

        elif path == "/api/request/tcp" and method == "POST":
            # Make TCP request(s) to backend (server-side batching)
            command = "test"
            req_backend = backend_host
            req_port = 9092
            amount = 1
            if request_body:
                try:
                    body_json = json.loads(request_body)
                    command = body_json.get("command", "test")
                    if 'backend' in body_json:
                        req_backend, req_port = parse_backend(body_json['backend'], backend_host, 9092)
                    amount = body_json.get('amount', 1)
                except json.JSONDecodeError:
                    pass

            # Make N concurrent requests to backend
            tasks = [make_tcp_request(command, req_backend, req_port, active_tcp_connections) for _ in range(amount)]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Filter out exceptions and track successful requests
            successful_results = []
            for result in results:
                if isinstance(result, dict):
                    successful_results.append(result)
                    # Track distribution server-side
                    server = result.get('server', 'unknown')
                    distribution_counts[server] = distribution_counts.get(server, 0) + 1
                    # Track latency (keep last 1000)
                    latency_stats["tcp"].append(result.get('latency_ms', 0))
                    if len(latency_stats["tcp"]) > 1000:
                        latency_stats["tcp"].pop(0)

            body = json.dumps({"results": successful_results, "total": amount, "successful": len(successful_results)})
            response = (
                "HTTP/1.0 200 OK\r\n"
                "Content-Type: application/json\r\n"
                "\r\n"
                f"{body}\n"
            ).encode('utf-8')

        elif path == "/stats":
            # JSON stats endpoint
            body = format_stats_json(http_counter, tcp_counter, start_time, latency_stats, active_tcp_connections)
            response = (
                "HTTP/1.0 200 OK\r\n"
                "Content-Type: application/json\r\n"
                "\r\n"
                f"{body}\n"
            ).encode('utf-8')

        elif path == "/api/distribution":
            # Distribution endpoint
            total = sum(distribution_counts.values())
            dist = {
                server: {
                    "count": count,
                    "percent": round(count / total * 100, 1) if total > 0 else 0
                }
                for server, count in sorted(distribution_counts.items(), key=lambda x: x[1], reverse=True)
            }
            body = json.dumps({
                "distribution": dist,
                "total": total,
                "timestamp": int(time.time())
            })
            response = (
                "HTTP/1.0 200 OK\r\n"
                "Content-Type: application/json\r\n"
                "\r\n"
                f"{body}\n"
            ).encode('utf-8')

        elif path == "/api/distribution/reset" and method == "POST":
            # Reset distribution counts
            old_total = sum(distribution_counts.values())
            distribution_counts.clear()
            body = json.dumps({
                "message": "Distribution reset",
                "cleared": old_total,
                "timestamp": int(time.time())
            })
            response = (
                "HTTP/1.0 200 OK\r\n"
                "Content-Type: application/json\r\n"
                "\r\n"
                f"{body}\n"
            ).encode('utf-8')

        elif path == "/api/connections/close-all" and method == "POST":
            # Stop cycling if active
            was_cycling = cycling_active['active']
            cycling_active['active'] = False
            if current_cycle_task['task'] and not current_cycle_task['task'].done():
                current_cycle_task['task'].cancel()
                try:
                    await current_cycle_task['task']
                except asyncio.CancelledError:
                    pass

            # Close all persistent TCP connections
            count = len(active_tcp_connections)
            close_tasks = []
            for writer in list(active_tcp_connections):
                writer.close()
                close_tasks.append(writer.wait_closed())

            # Wait for all connections to close (with timeout)
            try:
                await asyncio.wait_for(
                    asyncio.gather(*close_tasks, return_exceptions=True),
                    timeout=2.0
                )
            except asyncio.TimeoutError:
                logger.warning(f"Timeout closing {count} connections")

            active_tcp_connections.clear()
            logger.info(f"Closed {count} persistent TCP connections{' and stopped cycling' if was_cycling else ''}")

            body = json.dumps({
                "message": "All connections closed" + (" and cycling stopped" if was_cycling else ""),
                "closed": count,
                "cycling_stopped": was_cycling,
                "timestamp": int(time.time())
            })
            response = (
                "HTTP/1.0 200 OK\r\n"
                "Content-Type: application/json\r\n"
                "\r\n"
                f"{body}\n"
            ).encode('utf-8')

        elif path == "/api/connections/cycle" and method == "POST":
            # Cycle connections: ramp up over 20s, ramp down over 20s, repeat until stopped
            req_backend = backend_host
            req_port = 9092
            amount = 1

            if request_body:
                try:
                    body_json = json.loads(request_body)
                    backend_str = body_json.get('backend', f'{backend_host}:9092')
                    req_backend, req_port = parse_backend(backend_str, backend_host, 9092)
                    amount = body_json.get('amount', 1)
                    amount = max(1, min(amount, 1000))  # Cap at 1000
                except (json.JSONDecodeError, ValueError):
                    pass

            # Set cycling active flag
            cycling_active['active'] = True

            # Start background task for continuous cycling
            async def cycle_connections_loop():
                ramp_duration = 20.0  # seconds
                interval = ramp_duration / amount if amount > 0 else 1.0
                cycle_count = 0

                try:
                    logger.info(f"Cycle: starting continuous cycling with {amount} peak connections")

                    while cycling_active['active']:
                        cycle_count += 1
                        opened_writers = []

                        try:
                            # Ramp up: open connections gradually
                            logger.info(f"Cycle {cycle_count}: ramping up to {amount} connections")
                            for i in range(amount):
                                if not cycling_active['active']:
                                    break

                                try:
                                    reader, writer = await asyncio.open_connection(req_backend, req_port)
                                    # Send OPEN command
                                    writer.write(b"OPEN\n")
                                    await writer.drain()
                                    # Read response
                                    await reader.readline()

                                    active_tcp_connections.add(writer)
                                    opened_writers.append(writer)

                                    if i < amount - 1:  # Don't sleep after last one
                                        await asyncio.sleep(interval)
                                except asyncio.CancelledError:
                                    raise
                                except Exception as e:
                                    logger.error(f"Cycle {cycle_count}: failed to open connection {i+1}: {e}")

                            if not cycling_active['active']:
                                break

                            logger.info(f"Cycle {cycle_count}: peak reached with {len(opened_writers)} connections")

                            # Ramp down: close connections gradually
                            logger.info(f"Cycle {cycle_count}: ramping down")
                            for i, writer in enumerate(opened_writers):
                                if not cycling_active['active']:
                                    break

                                try:
                                    writer.close()
                                    await writer.wait_closed()
                                    active_tcp_connections.discard(writer)

                                    if i < len(opened_writers) - 1:  # Don't sleep after last one
                                        await asyncio.sleep(interval)
                                except asyncio.CancelledError:
                                    raise
                                except Exception as e:
                                    logger.error(f"Cycle {cycle_count}: failed to close connection {i+1}: {e}")

                            logger.info(f"Cycle {cycle_count}: complete")

                        except asyncio.CancelledError:
                            # Clean up connections on cancellation
                            for writer in opened_writers:
                                try:
                                    writer.close()
                                    await writer.wait_closed()
                                    active_tcp_connections.discard(writer)
                                except Exception:
                                    pass
                            raise

                    logger.info(f"Cycling stopped after {cycle_count} cycles")

                except asyncio.CancelledError:
                    logger.info(f"Cycling cancelled after {cycle_count} cycles")
                except Exception as e:
                    logger.error(f"Cycle: error during cycling: {e}")
                finally:
                    cycling_active['active'] = False

            # Fire and forget the cycle task
            current_cycle_task['task'] = asyncio.create_task(cycle_connections_loop())

            body = json.dumps({
                "message": "Continuous cycling started",
                "amount": amount,
                "cycle_duration": 40,
                "info": "Cycles will repeat until 'Close All' is pressed",
                "timestamp": int(time.time())
            })
            response = (
                "HTTP/1.0 200 OK\r\n"
                "Content-Type: application/json\r\n"
                "\r\n"
                f"{body}\n"
            ).encode('utf-8')

        elif path == "/openapi.json":
            # OpenAPI 3.0 specification
            spec = generate_openapi_spec(backend_host)
            body = json.dumps(spec, indent=2)
            response = (
                "HTTP/1.0 200 OK\r\n"
                "Content-Type: application/json\r\n"
                "Access-Control-Allow-Origin: *\r\n"
                "\r\n"
                f"{body}\n"
            ).encode('utf-8')

        else:
            # Dashboard HTML (root or /dashboard)
            html = render_dashboard_html(backend_host)
            response = (
                "HTTP/1.0 200 OK\r\n"
                "Content-Type: text/html\r\n"
                "\r\n"
                f"{html}"
            ).encode('utf-8')

        writer.write(response)
        await writer.drain()

    except asyncio.IncompleteReadError:
        logger.warning(f"Dashboard incomplete request from {addr}")
    except ValueError as e:
        # Likely a parsing error from backend response
        logger.error(f"Dashboard parsing error from {addr}: {e}")
        try:
            error_response = (
                "HTTP/1.0 502 Bad Gateway\r\n"
                "Content-Type: application/json\r\n"
                "\r\n"
                f'{{"error": "{str(e)}"}}\n'
            ).encode('utf-8')
            writer.write(error_response)
            await writer.drain()
        except Exception:
            pass
    except Exception as e:
        logger.error(f"Dashboard error from {addr}: {e}", exc_info=True)
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass


async def start_dashboard_server(
    host: str,
    port: int,
    http_counter: Counter,
    tcp_counter: Counter,
    start_time: float,
    backend_host: str = 'localhost'
) -> None:
    """Start dashboard server.

    Args:
        host: Bind address
        port: Port number (typically 9093)
        http_counter: HTTP counter instance
        tcp_counter: TCP counter instance
        start_time: Server start timestamp
        backend_host: Backend host for making requests (default: localhost)
    """
    # Server-side distribution tracking
    distribution_counts = {}  # {"server_id": count}

    # Latency tracking (keep last 1000 requests per protocol)
    latency_stats = {
        "http": [],  # List of latency_ms values
        "tcp": []    # List of latency_ms values
    }

    # Track persistent TCP connections (dashboard → backends)
    active_tcp_connections = set()  # Set[asyncio.StreamWriter]

    # Track cycling state
    cycling_active = {'active': False}  # Use dict for mutability in closures
    current_cycle_task = {'task': None}  # Current background cycle task

    async def handler(reader, writer):
        await dashboard_handler(reader, writer, http_counter, tcp_counter, start_time, backend_host, distribution_counts, latency_stats, active_tcp_connections, cycling_active, current_cycle_task)

    server = await asyncio.start_server(handler, host, port)
    addr = server.sockets[0].getsockname()
    logger.info(f"✓ Dashboard ready at http://{addr[0]}:{addr[1]}/")

    try:
        async with server:
            await server.serve_forever()
    finally:
        # Close all active persistent connections
        if active_tcp_connections:
            logger.info(f"Closing {len(active_tcp_connections)} active dashboard TCP connections...")
            close_tasks = []
            for writer in list(active_tcp_connections):
                writer.close()
                close_tasks.append(writer.wait_closed())
            try:
                await asyncio.wait_for(
                    asyncio.gather(*close_tasks, return_exceptions=True),
                    timeout=1.0
                )
            except asyncio.TimeoutError:
                logger.warning("Dashboard connection close timeout - forcing shutdown")
