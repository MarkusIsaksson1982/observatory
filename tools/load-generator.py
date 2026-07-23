"""Load generator for Observatory stack - Zero external dependencies.

Generates realistic traffic against the FastAPI gateway service to populate
Grafana dashboards with LIVE data for portfolio presentation.

Features:
  - Rate limiting with sliding window
  - Error injection (10-15% chance per endpoint)
  - Latency tracking per endpoint
  - Ctrl+C graceful shutdown with summary stats
  - Colored output with optional --no-color

Usage:
  python load-generator.py                    # defaults: rate=10, duration=120
  python load-generator.py --rate 5 --duration 30
  python load-generator.py --rate 20 --duration 300 --error-rate 0.2
  python load-generator.py --gateway http://192.168.1.100:8000
"""
import json
import os
import random
import sys
import threading
import time
import urllib.error
import urllib.request
from collections import defaultdict


# -- Config --

DEFAULT_GATEWAY = os.environ.get("GATEWAY_URL", "http://localhost:8000")
DEFAULT_RATE = 10        # requests per second
DEFAULT_DURATION = 120   # seconds
DEFAULT_ERROR_RATE = 0.12  # 12% error injection (simulates realistic failures)

# Endpoint registry: (method, path, payload, latency_label, error_weight)
ENDPOINTS = [
    ("GET",  "/health",         None,    "fast",    0.01),
    ("GET",  "/orders",         None,    "fast",    0.05),
    ("GET",  "/payments",       None,    "fast",    0.05),
    ("POST", "/checkout",       "{}",   "medium",   0.15),
    ("GET",  "/fibonacci",      None,    "slow",    0.08),
]

HEAVY_ENDPOINTS = [
    ("GET",  "/fibonacci",      None,    "slow",    0.08),
    ("POST", "/checkout",       "{}",   "medium",   0.15),
]


# -- Colored output --

class Colors:
    RESET   = ""
    BOLD    = ""
    RED     = ""
    GREEN   = ""
    YELLOW  = ""
    CYAN    = ""
    DIM     = ""

if sys.platform != "win32" or os.environ.get("FORCE_COLOR"):
    Colors.RESET   = "\033[0m"
    Colors.BOLD    = "\033[1m"
    Colors.RED     = "\033[31m"
    Colors.GREEN   = "\033[32m"
    Colors.YELLOW  = "\033[33m"
    Colors.CYAN    = "\033[36m"
    Colors.DIM     = "\033[2m"


# -- State --

class LoadGeneratorState:
    def __init__(self):
        self.lock = threading.Lock()
        self.running = True
        self.request_count = 0
        self.error_count = 0
        self.start_time = 0.0
        self.endpoint_latencies = defaultdict(list)
        self.endpoint_counts = defaultdict(int)
        self.endpoint_errors = defaultdict(int)
        self.status_codes = defaultdict(int)
        self.errors_by_type = defaultdict(int)


# -- HTTP helpers --

def http_request(url: str, method: str = "GET",
                 data: bytes | None = None,
                 timeout: int = 5) -> tuple[int, float]:
    """Make HTTP request, return (status_code, elapsed_ms)."""
    start = time.monotonic()
    try:
        req = urllib.request.Request(
            url,
            data=data,
            method=method,
            headers={"Content-Type": "application/json"} if data else {},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            elapsed_ms = (time.monotonic() - start) * 1000
            return resp.status, elapsed_ms
    except urllib.error.HTTPError as e:
        elapsed_ms = (time.monotonic() - start) * 1000
        return e.code, elapsed_ms
    except urllib.error.URLError:
        elapsed_ms = (time.monotonic() - start) * 1000
        return 0, elapsed_ms
    except OSError:
        elapsed_ms = (time.monotonic() - start) * 1000
        return 0, elapsed_ms


# -- Request worker --

def send_request(gateway_url: str, method: str, path: str,
                 payload: str | None, state: LoadGeneratorState,
                 error_rate: float = 0.12) -> None:
    """Send single request, record metrics."""
    url = f"{gateway_url}{path}"
    data = payload.encode("utf-8") if payload else None

    status, elapsed_ms = http_request(url, method=method, data=data)

    with state.lock:
        state.request_count += 1
        state.endpoint_counts[f"{method} {path}"] += 1
        state.endpoint_latencies[f"{method} {path}"].append(elapsed_ms)
        state.status_codes[status] += 1

        if status == 0:
            state.error_count += 1
            state.errors_by_type["connection"] += 1
        elif status >= 400:
            state.error_count += 1
            state.endpoint_errors[f"{method} {path}"] += 1
            if status >= 500:
                state.errors_by_type["server_error"] += 1
            elif status == 422:
                state.errors_by_type["validation"] += 1


# -- Rate limiter --

class SlidingWindowRateLimiter:
    """Token bucket rate limiter with sliding window."""

    def __init__(self, rate: float):
        self.rate = rate
        self.interval = 1.0 / rate if rate > 0 else float("inf")
        self.last_request = time.monotonic()
        self.lock = threading.Lock()

    def wait(self) -> None:
        """Block until next request slot is available."""
        with self.lock:
            now = time.monotonic()
            next_time = self.last_request + self.interval
            if next_time > now:
                time.sleep(next_time - now)
            self.last_request = time.monotonic()


# -- Generator loop --

def generate_load(state: LoadGeneratorState, gateway_url: str,
                  rate: float, duration: float,
                  error_rate: float = 0.12,
                  heavy_pct: float = 0.25) -> None:
    """Main load generation loop."""
    limiter = SlidingWindowRateLimiter(rate)
    end_time = time.monotonic() + duration
    thread_pool_size = min(rate * 2, 50) if rate <= 20 else 50
    thread_pool = []

    print(f"{Colors.GREEN}  [>>>] Generating load at {rate:.1f} req/s for {duration}s")
    print(f"        Gateway: {gateway_url}")
    print(f"        Threads: {thread_pool_size}  Error rate: {error_rate*100:.0f}%")
    print(f"        Heavy endpoint mix: {heavy_pct*100:.0f}%{Colors.RESET}\n")

    while state.running and time.monotonic() < end_time:
        limiter.wait()

        # Pick endpoint: heavy_pct chance for slow endpoints
        if random.random() < heavy_pct:
            endpoint = random.choice(HEAVY_ENDPOINTS)
        else:
            endpoint = random.choice(ENDPOINTS)

        method, path, payload, _, _ = endpoint

        # Error injection: send malformed payloads sometimes
        actual_payload = payload
        if error_rate > 0 and random.random() < error_rate:
            if method == "POST":
                actual_payload = json.dumps({"invalid": "injected"})
            # Also inject random order_id to trigger 404s
            elif "/orders/" in path:
                path = f"/orders/{random.randint(1000, 9999)}"
            elif method == "GET" and random.random() < 0.3:
                path = f"/nonexistent-{random.randint(1000,9999)}"

        # Fire request in thread pool
        t = threading.Thread(
            target=send_request,
            args=(gateway_url, method, path, actual_payload, state, error_rate),
            daemon=True,
        )
        t.start()
        thread_pool.append(t)

        # Clean up finished threads periodically
        if len(thread_pool) > thread_pool_size * 2:
            thread_pool = [t for t in thread_pool if t.is_alive()]

    # Wait for in-flight requests
    for t in thread_pool:
        t.join(timeout=2)


# -- Summary printer --

def print_summary(state: LoadGeneratorState) -> None:
    """Print final load test summary with colored output."""
    elapsed = time.monotonic() - state.start_time
    rps = state.request_count / elapsed if elapsed > 0 else 0

    print(f"\n{Colors.BOLD}{'='*60}")
    print("  LOAD TEST SUMMARY")
    print(f"{'='*60}{Colors.RESET}")
    print(f"  Duration:       {elapsed:.1f}s")
    print(f"  Total requests: {state.request_count}")
    print(f"  Requests/sec:   {rps:.2f}")
    print(f"  Errors:         {state.error_count} "
          f"({(state.error_count/state.request_count*100):.1f}%)" if state.request_count else "")

    if state.status_codes:
        print(f"\n  {Colors.CYAN}Status Codes:{Colors.RESET}")
        for code in sorted(state.status_codes):
            color = Colors.GREEN if 200 <= code < 300 else Colors.RED if code >= 400 else Colors.YELLOW
            print(f"    {color}{code}{Colors.RESET}: {state.status_codes[code]}")

    if state.endpoint_latencies:
        print(f"\n  {Colors.CYAN}Latency by Endpoint:{Colors.RESET}")
        for endpoint, latencies in sorted(state.endpoint_latencies.items()):
            if not latencies:
                continue
            avg = sum(latencies) / len(latencies)
            p95 = sorted(latencies)[int(len(latencies) * 0.95)]
            errs = state.endpoint_errors.get(endpoint, 0)
            count = state.endpoint_counts[endpoint]
            color = Colors.RED if errs > 0 else Colors.GREEN
            print(f"    {color}{endpoint}{Colors.RESET}")
            print(f"      count: {count}  avg: {avg:.1f}ms  p95: {p95:.1f}ms"
                  f"  errors: {errs}")

    if state.errors_by_type:
        print(f"\n  {Colors.YELLOW}Error Breakdown:{Colors.RESET}")
        for etype, count in sorted(state.errors_by_type.items()):
            print(f"    {etype}: {count}")

    print(f"\n{Colors.GREEN}  [DONE]{Colors.RESET}")


# -- CLI --

def parse_args():
    """Parse CLI arguments (no external deps)."""
    args = {
        "gateway": DEFAULT_GATEWAY,
        "rate": DEFAULT_RATE,
        "duration": DEFAULT_DURATION,
        "error-rate": DEFAULT_ERROR_RATE,
        "heavy-pct": 0.25,
        "color": True,
    }

    positional = []
    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == "--gateway" and i + 1 < len(sys.argv):
            args["gateway"] = sys.argv[i + 1]
            i += 2
        elif arg == "--rate" and i + 1 < len(sys.argv):
            args["rate"] = float(sys.argv[i + 1])
            i += 2
        elif arg == "--duration" and i + 1 < len(sys.argv):
            args["duration"] = float(sys.argv[i + 1])
            i += 2
        elif arg == "--error-rate" and i + 1 < len(sys.argv):
            args["error-rate"] = float(sys.argv[i + 1])
            i += 2
        elif arg == "--heavy-pct" and i + 1 < len(sys.argv):
            args["heavy-pct"] = float(sys.argv[i + 1])
            i += 2
        elif arg == "--no-color":
            args["color"] = False
            i += 1
        elif arg in ("-h", "--help"):
            print(__doc__)
            sys.exit(0)
        else:
            positional.append(arg)
            i += 1

    if not args["color"]:
        Colors.RESET = ""
        Colors.BOLD = ""
        Colors.RED = ""
        Colors.GREEN = ""
        Colors.YELLOW = ""
        Colors.CYAN = ""
        Colors.DIM = ""

    return args


def verify_gateway(url: str) -> bool:
    """Quick health check before starting."""
    try:
        req = urllib.request.Request(f"{url}/health", method="GET")
        with urllib.request.urlopen(req, timeout=3) as resp:
            return resp.status == 200
    except (urllib.error.URLError, OSError):
        return False


# -- Main --

def main() -> int:
    args = parse_args()
    state = LoadGeneratorState()

    print(f"{Colors.BOLD}  Observatory Load Generator{Colors.RESET}")
    print(f"  {Colors.DIM}{'-'*40}{Colors.RESET}")

    # Pre-flight check
    print(f"\n  Checking gateway at {args['gateway']}...", end="", flush=True)
    if not verify_gateway(args["gateway"]):
        print(f"\n  {Colors.RED}[FAIL]{Colors.RESET} Gateway unreachable at {args['gateway']}")
        print("  Is docker-compose up? Run: docker-compose up -d")
        return 1
    print(f" {Colors.GREEN}[OK]{Colors.RESET}")

    # Validate rate
    if args["rate"] <= 0:
        print(f"\n  {Colors.RED}[FAIL]{Colors.RESET} Rate must be positive (got {args['rate']})")
        return 1
    if args["rate"] > 100:
        print(f"\n  {Colors.YELLOW}[WARN]{Colors.RESET} Rate {args['rate']} is very high for a local demo")

    # Register Ctrl+C handler
    def shutdown_handler(sig=None, frame=None):
        state.running = False
        print(f"\n  {Colors.YELLOW}[INTERRUPTED]{Colors.RESET} Shutting down gracefully...")
    try:
        import signal
        signal.signal(signal.SIGINT, shutdown_handler)
        signal.signal(signal.SIGTERM, shutdown_handler)
    except (AttributeError, OSError):
        pass

    # Run
    state.start_time = time.monotonic()
    try:
        generate_load(
            state=state,
            gateway_url=args["gateway"],
            rate=args["rate"],
            duration=args["duration"],
            error_rate=args["error-rate"],
            heavy_pct=args["heavy-pct"],
        )
    except KeyboardInterrupt:
        shutdown_handler()
    finally:
        print_summary(state)

    return 0


if __name__ == "__main__":
    sys.exit(main())
