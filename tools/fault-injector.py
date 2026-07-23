#!/usr/bin/env python3
"""
Observatory fault injector.

Purpose:
  Deliberately generate controlled failure traffic against the gateway so the
  availability SLO, burn-rate recording rules, and SLO dashboard become
  demonstrable instead of permanently quiet.

This is OPT-IN. It is intended for local portfolio/demo use only.

Current assumption:
  The demo stack currently runs only the gateway service. The endpoints
  /orders, /payments, and /checkout therefore return HTTP 503 because their
  downstream services are absent. Those 503 responses should create server-side
  error spans, which Tempo's metrics-generator should expose as:

    status_code="STATUS_CODE_ERROR"

  That is the label used by the availability SLO in sloth/gateway-slo.yaml.

Usage examples:
  # Check whether the current stack can generate 5xx responses:
  python tools/fault-injector.py --probe-only

  # Sustained fault injection for 5 minutes:
  python tools/fault-injector.py --duration 300 --rate 10 --error-ratio 0.3

  # Harder burn:
  python tools/fault-injector.py --duration 600 --rate 20 --error-ratio 0.8

  # Custom endpoints:
  python tools/fault-injector.py \
    --healthy "GET /health,GET /fibonacci?n=10" \
    --fault "GET /orders,GET /payments,POST /checkout"

Notes:
  - This script uses only the Python standard library.
  - It sends W3C traceparent headers so generated traces are easy to correlate.
  - It does not modify any service code.
  - If you later add healthy orders/payments services, update --fault endpoints
    to something that actually fails.
"""

import argparse
import os
import random
import secrets
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, wait


DEFAULT_GATEWAY = os.environ.get("GATEWAY_URL", "http://localhost:8000")

DEFAULT_HEALTHY_ENDPOINTS = "GET /health,GET /fibonacci?n=10"
DEFAULT_FAULT_ENDPOINTS = "GET /orders"


class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    CYAN = "\033[36m"
    DIM = "\033[2m"


def make_colors(enabled: bool):
    if enabled:
        return Colors

    class _NoColors:
        RESET = ""
        BOLD = ""
        RED = ""
        GREEN = ""
        YELLOW = ""
        CYAN = ""
        DIM = ""

    return _NoColors()


def parse_endpoints(spec: str):
    """
    Parse endpoint specs.

    Accepted forms:
      "GET /health"
      "/health"
      "POST /checkout"

    Multiple endpoints are comma-separated.
    """
    endpoints = []

    for item in spec.split(","):
        item = item.strip()
        if not item:
            continue

        parts = item.split(maxsplit=1)

        if len(parts) == 1:
            path = parts[0]
            method = "POST" if path.rstrip("/").endswith("/checkout") else "GET"
        else:
            method = parts[0].upper()
            path = parts[1]

        endpoints.append((method, path))

    if not endpoints:
        raise ValueError("no endpoints parsed")

    return endpoints


def build_headers(correlation_prefix: str):
    trace_id = secrets.token_hex(16)
    span_id = secrets.token_hex(8)

    return {
        "traceparent": f"00-{trace_id}-{span_id}-01",
        "X-Correlation-ID": f"{correlation_prefix}-{trace_id[:8]}",
        "User-Agent": "observatory-fault-injector/1.0",
    }


def send_one(base_url: str, method: str, path: str, timeout: float, correlation_prefix: str):
    """
    Send one HTTP request and return (status_code, elapsed_ms).

    Status code 0 means the request failed at the network level.
    """
    url = base_url.rstrip("/") + path
    headers = build_headers(correlation_prefix)
    data = None

    if method.upper() == "POST":
        data = b"{}"
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(
        url,
        data=data,
        method=method.upper(),
        headers=headers,
    )

    start = time.monotonic()

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = resp.status
            _ = resp.read(16)

    except urllib.error.HTTPError as e:
        status = e.code
        try:
            _ = e.read(16)
        except Exception:
            pass

    except Exception:
        status = 0

    elapsed_ms = (time.monotonic() - start) * 1000.0
    return status, elapsed_ms


class State:
    def __init__(self):
        self.lock = threading.Lock()
        self.total = 0
        self.healthy_requests = 0
        self.fault_requests = 0
        self.server_errors = 0
        self.client_errors = 0
        self.connection_errors = 0
        self.statuses = {}
        self.latency_sum_ms = 0.0


def record_result(state: State, is_fault: bool, status: int, elapsed_ms: float):
    with state.lock:
        state.total += 1
        state.latency_sum_ms += elapsed_ms

        if is_fault:
            state.fault_requests += 1
        else:
            state.healthy_requests += 1

        state.statuses[status] = state.statuses.get(status, 0) + 1

        if status == 0:
            state.connection_errors += 1
        elif 400 <= status < 500:
            state.client_errors += 1
        elif status >= 500:
            state.server_errors += 1


def worker(
    base_url: str,
    method: str,
    path: str,
    timeout: float,
    correlation_prefix: str,
    is_fault: bool,
    state: State,
):
    status, elapsed_ms = send_one(
        base_url=base_url,
        method=method,
        path=path,
        timeout=timeout,
        correlation_prefix=correlation_prefix,
    )
    record_result(state, is_fault, status, elapsed_ms)


def status_color(status: int, c):
    if status == 0:
        return c.RED
    if 200 <= status < 300:
        return c.GREEN
    if 400 <= status < 500:
        return c.YELLOW
    if status >= 500:
        return c.RED
    return c.CYAN


def run_probe(base_url: str, healthy_endpoints, fault_endpoints, timeout: float, c):
    print(f"{c.BOLD}Probe mode{c.RESET}")
    print(f"Gateway: {base_url}")
    print()

    endpoints = []
    endpoints.extend([("healthy", m, p) for m, p in healthy_endpoints])
    endpoints.extend([("fault", m, p) for m, p in fault_endpoints])

    reachable = False
    saw_5xx = False

    for kind, method, path in endpoints:
        status, elapsed_ms = send_one(
            base_url=base_url,
            method=method,
            path=path,
            timeout=timeout,
            correlation_prefix="fault-probe",
        )

        if kind == "healthy" and status != 0:
            reachable = True

        if kind == "fault" and status >= 500:
            saw_5xx = True

        color = status_color(status, c)

        print(
            f"{kind:8} {method:6} {path:32} -> "
            f"{color}{status}{c.RESET} ({elapsed_ms:7.1f} ms)"
        )

    print()

    if not reachable:
        print(
            f"{c.RED}[FAIL]{c.RESET} "
            "Gateway did not respond to healthy probe requests."
        )
        return reachable, saw_5xx

    if not saw_5xx:
        print(
            f"{c.YELLOW}[WARN]{c.RESET} "
            "No fault endpoint returned HTTP 5xx.\n"
            "       The availability SLO probably will not burn with these endpoints.\n"
            "       In the current single-service demo, /orders, /payments, and /checkout\n"
            "       should return 503 because downstream services are absent.\n"
            "       If you later add healthy downstream services, choose endpoints that fail."
        )
    else:
        print(
            f"{c.GREEN}[OK]{c.RESET} "
            "At least one fault endpoint returned HTTP 5xx."
        )

    return reachable, saw_5xx


def print_summary(state: State, actual_duration_s: float, sent: int, c):
    with state.lock:
        total = state.total
        healthy = state.healthy_requests
        fault = state.fault_requests
        server_errors = state.server_errors
        client_errors = state.client_errors
        connection_errors = state.connection_errors
        statuses = dict(state.statuses)
        latency_sum_ms = state.latency_sum_ms

    print()
    print(f"{c.BOLD}Fault injection summary{c.RESET}")
    print(f"  Actual duration:      {actual_duration_s:.1f}s")
    print(f"  Requests submitted:   {sent}")
    print(f"  Requests completed:   {total}")
    print(f"  Healthy requests:     {healthy}")
    print(f"  Fault requests:       {fault}")
    print(f"  HTTP 5xx responses:   {server_errors}")
    print(f"  HTTP 4xx responses:   {client_errors}")
    print(f"  Network failures:     {connection_errors}")

    if total > 0:
        avg_latency_ms = latency_sum_ms / total
        server_error_ratio = server_errors / total

        print(f"  Avg latency:          {avg_latency_ms:.1f} ms")
        print(f"  Observed 5xx ratio:   {server_error_ratio * 100:.2f}%")

    if statuses:
        print()
        print("  Status codes:")
        for status in sorted(statuses):
            label = "network" if status == 0 else str(status)
            color = status_color(status, c)
            print(f"    {color}{label:>8}{c.RESET}: {statuses[status]}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Opt-in fault injector for the Observatory demo stack.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--gateway",
        default=DEFAULT_GATEWAY,
        help=f"Gateway base URL. Default: {DEFAULT_GATEWAY}",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=300.0,
        help="Sustained injection duration in seconds. Default: 300",
    )
    parser.add_argument(
        "--rate",
        type=float,
        default=10.0,
        help="Target requests per second. Default: 10",
    )
    parser.add_argument(
        "--error-ratio",
        type=float,
        default=0.30,
        help=(
            "Fraction of requests sent to fault endpoints. "
            "Accepts 0.0-1.0 or 0-100. Default: 0.30"
        ),
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=5.0,
        help="HTTP timeout in seconds. Default: 5",
    )
    parser.add_argument(
        "--healthy",
        default=DEFAULT_HEALTHY_ENDPOINTS,
        help=(
            "Comma-separated healthy endpoints. "
            f"Default: {DEFAULT_HEALTHY_ENDPOINTS}"
        ),
    )
    parser.add_argument(
        "--fault",
        default=DEFAULT_FAULT_ENDPOINTS,
        help=(
            "Comma-separated fault endpoints expected to return 5xx. "
            "In the current demo stack, only '/orders' reliably returns 503. "
            f"Default: {DEFAULT_FAULT_ENDPOINTS}"
        ),
    )
    parser.add_argument(
        "--max-requests",
        type=int,
        default=None,
        help="Optional hard cap on number of submitted requests.",
    )
    parser.add_argument(
        "--probe-only",
        action="store_true",
        help="Send one probe request per endpoint and exit.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero if no HTTP 5xx responses were observed.",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable colored output.",
    )

    args = parser.parse_args()

    try:
        healthy_endpoints = parse_endpoints(args.healthy)
        fault_endpoints = parse_endpoints(args.fault)
    except ValueError as e:
        parser.error(str(e))

    error_ratio = args.error_ratio
    if error_ratio > 1.0:
        error_ratio = error_ratio / 100.0

    if error_ratio < 0.0 or error_ratio > 1.0:
        parser.error("--error-ratio must be between 0 and 1, or between 0 and 100.")

    if args.rate <= 0.0:
        parser.error("--rate must be greater than zero.")

    if args.duration <= 0.0 and not args.probe_only:
        parser.error("--duration must be greater than zero.")

    if args.timeout <= 0.0:
        parser.error("--timeout must be greater than zero.")

    colors_enabled = not args.no_color and sys.stdout.isatty()
    c = make_colors(colors_enabled)

    if args.probe_only:
        reachable, saw_5xx = run_probe(
            base_url=args.gateway,
            healthy_endpoints=healthy_endpoints,
            fault_endpoints=fault_endpoints,
            timeout=args.timeout,
            c=c,
        )

        if not reachable:
            return 1

        if args.strict and not saw_5xx:
            return 1

        return 0

    print(f"{c.BOLD}Observatory fault injector{c.RESET}")
    print(f"{c.YELLOW}OPT-IN: deliberately generating failure traffic.{c.RESET}")
    print()
    print(f"Gateway:        {args.gateway}")
    print(f"Duration:       {args.duration:.0f}s")
    print(f"Target rate:    {args.rate:.1f} req/s")
    print(f"Error ratio:    {error_ratio * 100:.1f}%")
    print(f"Timeout:        {args.timeout:.1f}s")
    print(f"Healthy endpoints:")
    for method, path in healthy_endpoints:
        print(f"  {method:6} {path}")
    print(f"Fault endpoints:")
    for method, path in fault_endpoints:
        print(f"  {method:6} {path}")
    print()
    print("Press Ctrl+C to stop early.")
    print()

    state = State()
    stop_event = threading.Event()

    max_workers = max(4, min(int(args.rate * 2) + 2, 64))
    executor = ThreadPoolExecutor(max_workers=max_workers)

    sent = 0
    start = time.monotonic()
    end = start + args.duration
    interval = 1.0 / args.rate
    next_send_time = start
    futures = []

    correlation_prefix = "fault-injector"

    try:
        while not stop_event.is_set():
            now = time.monotonic()

            if now >= end:
                break

            if args.max_requests is not None and sent >= args.max_requests:
                break

            if now < next_send_time:
                time.sleep(min(next_send_time - now, 0.02))
                continue

            if random.random() < error_ratio:
                method, path = random.choice(fault_endpoints)
                is_fault = True
            else:
                method, path = random.choice(healthy_endpoints)
                is_fault = False

            future = executor.submit(
                worker,
                args.gateway,
                method,
                path,
                args.timeout,
                correlation_prefix,
                is_fault,
                state,
            )

            futures.append(future)
            sent += 1

            next_send_time += interval

            if next_send_time < now:
                next_send_time = now + interval

            if len(futures) > max_workers * 4:
                futures = [f for f in futures if not f.done()]

    except KeyboardInterrupt:
        stop_event.set()
        print()
        print(f"{c.YELLOW}Interrupt received; stopping early...{c.RESET}")

    finally:
        wait(futures, timeout=args.timeout + 5.0)
        executor.shutdown(wait=False, cancel_futures=True)

    actual_duration = time.monotonic() - start

    print_summary(state, actual_duration, sent, c)

    with state.lock:
        total = state.total
        server_errors = state.server_errors
        connection_errors = state.connection_errors

    print()

    if total == 0:
        print(
            f"{c.RED}[FAIL]{c.RESET} "
            "No requests completed. Check that the gateway is running and reachable."
        )
        return 1

    if connection_errors > total * 0.2:
        print(
            f"{c.YELLOW}[WARN]{c.RESET} "
            "A large fraction of requests failed at the network level. "
            "Those do not create gateway server spans and will not help the SLO."
        )

    if server_errors == 0:
        print(
            f"{c.YELLOW}[WARN]{c.RESET} "
            "No HTTP 5xx responses were observed.\n"
            "       The availability SLO probably did not burn.\n"
            "       In the current single-service demo, /orders, /payments, and /checkout\n"
            "       should return 503 because downstream services are absent.\n"
            "       If those endpoints are now healthy, choose different --fault endpoints."
        )

        if args.strict:
            return 1

        return 0

    server_error_ratio = server_errors / total

    if actual_duration < 300.0:
        print(
            f"{c.CYAN}[INFO]{c.RESET} "
            f"Run duration was {actual_duration:.0f}s. "
            "For the 5m Sloth window, run at least 300s to see stable burn-rate data."
        )

    if server_error_ratio > 0.0144:
        print(
            f"{c.GREEN}[INFO]{c.RESET} "
            f"Observed 5xx ratio {server_error_ratio * 100:.2f}% is above the "
            "approximate fast-burn page threshold of 1.44% for a 99.9% availability SLO.\n"
            "       If Tempo marks these 5xx server spans as STATUS_CODE_ERROR, the "
            "availability burn-rate panels should become non-empty after metric ingestion "
            "and rule evaluation catch up."
        )
    else:
        print(
            f"{c.CYAN}[INFO]{c.RESET} "
            f"Observed 5xx ratio {server_error_ratio * 100:.2f}% is below the "
            "approximate fast-burn page threshold of 1.44%.\n"
            "       Increase --error-ratio or --duration for a clearer demo."
        )

    print()
    print(
        f"{c.DIM}"
        "Verification tip:\n"
        "  After running, query Mimir for recent gateway server error spans, e.g.:\n"
        "\n"
        "    sum(rate(\n"
        "      traces_spanmetrics_latency_count{\n"
        "        service=\"gateway\",\n"
        "        span_kind=\"SPAN_KIND_SERVER\",\n"
        "        status_code=\"STATUS_CODE_ERROR\"\n"
        "      }[5m]\n"
        "    ))\n"
        "\n"
        "  The exact Prometheus API path may be /api/v1/query or /prometheus/api/v1/query\n"
        "  depending on your Mimir api_prefix configuration.\n"
        f"{c.RESET}"
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
