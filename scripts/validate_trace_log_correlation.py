#!/usr/bin/env python3
"""
Validate Observatory trace/log correlation.

This script:
  1. Generates a known W3C traceparent.
  2. Sends traffic to the gateway.
  3. Checks Loki for logs containing that trace ID.
  4. Checks Tempo for the trace.
  5. Reports PASS/WARN/FAIL.

It uses only the Python standard library.

Usage:
  python scripts/validate_trace_log_correlation.py
  GATEWAY_URL=http://localhost:8000 python scripts/validate_trace_log_correlation.py
"""

import argparse
import base64
import json
import os
import secrets
import sys
import time
import urllib.error
import urllib.parse
import urllib.request


PASS = "PASS"
WARN = "WARN"
FAIL = "FAIL"


def env(name: str, default: str) -> str:
    return os.getenv(name, default)


def http_request(url: str, timeout: float = 5.0, headers=None, auth=None):
    """
    Simple HTTP GET helper.

    Returns:
        (status_code, parsed_json_or_empty_dict, raw_body_or_error)
    """
    headers = dict(headers or {})

    if auth:
        username, password = auth
        token = base64.b64encode(f"{username}:{password}".encode()).decode()
        headers["Authorization"] = f"Basic {token}"

    req = urllib.request.Request(url, headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", "replace")
            try:
                return resp.status, json.loads(body), body
            except json.JSONDecodeError:
                return resp.status, {}, body

    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        try:
            return e.code, json.loads(body), body
        except json.JSONDecodeError:
            return e.code, {}, body

    except Exception as e:
        return None, {}, str(e)


def generate_traffic(gateway_url: str, trace_id: str):
    """
    Generate gateway traffic using a known trace ID.

    The /orders endpoint is intentionally included because it emits logs
    even when the downstream orders service is unavailable.
    """
    paths = [
        "/health",
        "/fibonacci?n=10",
        "/orders",
    ]

    results = {}

    for path in paths:
        span_id = secrets.token_hex(8)
        traceparent = f"00-{trace_id}-{span_id}-01"

        headers = {
            "traceparent": traceparent,
            "X-Correlation-ID": f"validate-{trace_id[:12]}",
        }

        url = gateway_url.rstrip("/") + path
        status, _, body = http_request(url, timeout=10.0, headers=headers)
        results[path] = status

        if status is None:
            return False, results

    return True, results


def wait_until(fn, attempts: int = 15, delay: float = 2.0):
    """
    Retry fn() until it returns (True, detail).
    """
    last_detail = "no detail"

    for _ in range(attempts):
        ok, detail = fn()
        if ok:
            return True, detail

        last_detail = detail
        time.sleep(delay)

    return False, last_detail


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate trace/log correlation for Observatory."
    )

    parser.add_argument(
        "--gateway-url",
        default=env("GATEWAY_URL", "http://localhost:8000"),
    )
    parser.add_argument(
        "--alloy-url",
        default=env("ALLOY_URL", "http://localhost:12345"),
    )
    parser.add_argument(
        "--loki-url",
        default=env("LOKI_URL", "http://localhost:3100"),
    )
    parser.add_argument(
        "--tempo-url",
        default=env("TEMPO_URL", "http://localhost:3200"),
    )
    parser.add_argument(
        "--grafana-url",
        default=env("GRAFANA_URL", "http://localhost:3000"),
    )
    parser.add_argument(
        "--grafana-user",
        default=env("GRAFANA_USER", "admin"),
    )
    parser.add_argument(
        "--grafana-password",
        default=env("GRAFANA_PASSWORD", "admin"),
    )
    parser.add_argument(
        "--no-grafana-auth",
        action="store_true",
        help="Do not use Grafana basic auth.",
    )
    parser.add_argument(
        "--skip-loki-trace",
        action="store_true",
        help="Skip Loki traceID log validation.",
    )
    parser.add_argument(
        "--skip-tempo-trace",
        action="store_true",
        help="Skip Tempo trace validation.",
    )
    parser.add_argument(
        "--wait-attempts",
        type=int,
        default=15,
    )
    parser.add_argument(
        "--wait-delay",
        type=float,
        default=2.0,
    )
    parser.add_argument(
        "--strict-warnings",
        action="store_true",
        help="Treat warnings as failures.",
    )

    args = parser.parse_args()

    results = []

    def add(name: str, status: str, detail: str = "") -> None:
        results.append((name, status, detail))

    trace_id = secrets.token_hex(16)

    print(f"Trace ID: {trace_id}")
    print()

    # ------------------------------------------------------------------
    # Basic service health
    # ------------------------------------------------------------------

    status, payload, body = http_request(f"{args.gateway_url}/health")
    add(
        "gateway_health",
        PASS if status == 200 else FAIL,
        f"HTTP {status}",
    )

    status, payload, body = http_request(f"{args.alloy_url}/-/healthy")
    add(
        "alloy_health",
        PASS if status == 200 else FAIL,
        f"HTTP {status}",
    )

    status, payload, body = http_request(f"{args.loki_url}/ready")
    add(
        "loki_ready",
        PASS if status == 200 else FAIL,
        f"HTTP {status}",
    )

    status, payload, body = http_request(f"{args.tempo_url}/ready")
    add(
        "tempo_ready",
        PASS if status == 200 else FAIL,
        f"HTTP {status}",
    )

    status, payload, body = http_request(f"{args.grafana_url}/api/health")
    add(
        "grafana_health",
        PASS if status == 200 else WARN,
        f"HTTP {status}",
    )

    # ------------------------------------------------------------------
    # Generate traffic with known traceparent
    # ------------------------------------------------------------------

    reachable, traffic = generate_traffic(args.gateway_url, trace_id)

    add(
        "traffic_generation",
        PASS if reachable else FAIL,
        json.dumps(traffic),
    )

    if not reachable:
        print("Gateway unreachable; skipping correlation checks.")
        print()

    # ------------------------------------------------------------------
    # Loki label sanity
    # ------------------------------------------------------------------

    status, payload, body = http_request(f"{args.loki_url}/loki/api/v1/labels")

    labels = []
    if isinstance(payload, dict):
        labels = payload.get("data", [])

    if status == 200 and "service_name" in labels:
        add(
            "loki_label_service_name",
            PASS,
            "service_name label present",
        )
    elif status == 200:
        add(
            "loki_label_service_name",
            WARN,
            f"service_name missing; labels={labels}",
        )
    else:
        add(
            "loki_label_service_name",
            FAIL,
            f"HTTP {status}",
        )

    # ------------------------------------------------------------------
    # Loki traceID log validation
    # ------------------------------------------------------------------

    if args.skip_loki_trace:
        add(
            "loki_trace_log",
            WARN,
            "skipped",
        )
    elif reachable:
        # Use query_range with explicit time window instead of instant query.
        # Loki instant query can miss logs in the head chunk (ingester buffer
        # not yet flushed to store). query_range with start/end covers head
        # chunk data reliably.
        import time as _time
        now_ns = int(_time.time() * 1e9)
        start_ns = now_ns - 5 * 60 * 1_000_000_000  # 5 minutes back

        # correlation_id is Loki structured metadata (promoted from OTLP
        # log attributes), NOT a stream label or body text. Loki 3.x queries
        # structured metadata with pipe syntax: | field_name="value".
        correlation_prefix = f"validate-{trace_id[:12]}"

        queries = [
            '{service_name="gateway"} | correlation_id =~ "validate-.*"',
            f'{{service_name="gateway"}} | correlation_id = "{correlation_prefix}"',
            f'{{service_name="gateway"}} |= "{correlation_prefix}"',
        ]

        def check_logs():
            for q in queries:
                params = urllib.parse.urlencode(
                    {
                        "query": q,
                        "start": str(start_ns),
                        "end": str(now_ns),
                        "limit": "10",
                    }
                )

                url = f"{args.loki_url}/loki/api/v1/query_range?{params}"
                status, payload, body = http_request(url, timeout=10.0)

                result = []
                if isinstance(payload, dict):
                    result = payload.get("data", {}).get("result", [])

                if status == 200 and result:
                    return True, f"query={q}"

            return False, f"no log found for correlation_id={correlation_prefix}"

        ok, detail = wait_until(
            check_logs,
            attempts=args.wait_attempts,
            delay=args.wait_delay,
        )

        add(
            "loki_trace_log",
            PASS if ok else FAIL,
            detail,
        )
    else:
        add(
            "loki_trace_log",
            FAIL,
            "skipped because gateway was unreachable",
        )

    # ------------------------------------------------------------------
    # Tempo trace validation
    # ------------------------------------------------------------------

    if args.skip_tempo_trace:
        add(
            "tempo_trace",
            WARN,
            "skipped",
        )
    elif reachable:
        url = f"{args.tempo_url}/api/search?tags=service.name%3Dgateway&limit=5"

        def check_trace():
            status, payload, body = http_request(url, timeout=5.0)

            if status == 200 and isinstance(payload, dict):
                traces = payload.get("traces", [])
                if traces:
                    return True, f"traces found={len(traces)}"

            return False, f"HTTP {status}"

        ok, detail = wait_until(
            check_trace,
            attempts=args.wait_attempts,
            delay=args.wait_delay,
        )

        add(
            "tempo_trace",
            PASS if ok else FAIL,
            detail,
        )
    else:
        add(
            "tempo_trace",
            FAIL,
            "skipped because gateway was unreachable",
        )

    # ------------------------------------------------------------------
    # Grafana datasource validation
    # ------------------------------------------------------------------

    grafana_auth = None
    if not args.no_grafana_auth and args.grafana_user:
        grafana_auth = (args.grafana_user, args.grafana_password)

    status, payload, body = http_request(
        f"{args.grafana_url}/api/datasources",
        auth=grafana_auth,
    )

    if status == 200 and isinstance(payload, list):
        uids = {ds.get("uid") for ds in payload if isinstance(ds, dict)}
        missing = {"loki", "tempo"} - uids

        if not missing:
            add(
                "grafana_datasources",
                PASS,
                f"uids={sorted(uids)}",
            )
        else:
            add(
                "grafana_datasources",
                WARN,
                f"missing={sorted(missing)}; uids={sorted(uids)}",
            )

    elif status in (401, 403):
        add(
            "grafana_datasources",
            WARN,
            f"HTTP {status}; auth required or insufficient",
        )
    else:
        add(
            "grafana_datasources",
            WARN,
            f"HTTP {status}",
        )

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    name_width = max(len(name) for name, _, _ in results) if results else 20

    print("Validation results:")
    print()

    for name, status, detail in results:
        print(f"{status:<5} {name.ljust(name_width)} {detail}")

    print()

    failed = any(status == FAIL for _, status, _ in results)
    warned = any(status == WARN for _, status, _ in results)

    if failed:
        print("Result: FAIL")
        return 1

    if warned and args.strict_warnings:
        print("Result: FAIL due to --strict-warnings")
        return 1

    if warned:
        print("Result: PASS with warnings")
    else:
        print("Result: PASS")

    return 0


if __name__ == "__main__":
    sys.exit(main())
