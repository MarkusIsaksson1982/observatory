"""Capture dashboard screenshots during active fault injection.

Orchestrates the full sequence:
  1. Start fault injector in background
  2. Wait for burn to stabilize
  3. Capture screenshots WHILE fault injector is still running
  4. Stop fault injector

This ensures SLO stat panels show active burn, not recovery.

Usage:
  python tools/capture-screenshots.py                          # defaults: 30min burn, 1200x600
  python tools/capture-screenshots.py --burn-minutes 15       # shorter burn for testing
  python tools/capture-screenshots.py --dry-run                # print commands without executing
"""
import argparse
import os
import signal
import subprocess
import sys
import time
import urllib.request
import urllib.error

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
FAULT_INJECTOR = os.path.join(SCRIPT_DIR, "fault-injector.py")

GRAFANA_URL = os.environ.get("GRAFANA_URL", "http://localhost:3000")
GRAFANA_USER = os.environ.get("GRAFANA_USER", "admin")
GRAFANA_PASS = os.environ.get("GRAFANA_PASS", "admin")

DASHBOARDS = [
    ("slo-burn-rate", "docs/screenshots/slo-burn-rate-active-burn.png"),
    ("service-health-red", "docs/screenshots/service-health-red-active-burn.png"),
    ("system-overview", "docs/screenshots/system-overview-active-burn.png"),
]


def wait_for_grafana(timeout=60):
    """Wait until Grafana is responding."""
    print("  Waiting for Grafana...", end="", flush=True)
    start = time.time()
    while time.time() - start < timeout:
        try:
            req = urllib.request.Request(f"{GRAFANA_URL}/api/health")
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status == 200:
                    print(" OK")
                    return True
        except (urllib.error.URLError, OSError):
            pass
        time.sleep(2)
    print(" TIMEOUT")
    return False


def capture_screenshot(dashboard_uid, output_path, width=1200, height=600, time_range="now-1h"):
    """Capture a single dashboard screenshot via Grafana Image Renderer."""
    render_url = (
        f"{GRAFANA_URL}/render/d/{dashboard_uid}"
        f"?orgId=1&from={time_range.split(' ')[0]}&to=now"
        f"&width={width}&height={height}"
    )

    # Use basic auth via urllib
    password_mgr = urllib.request.HTTPPasswordMgrWithDefaultRealm()
    password_mgr.add_password(None, GRAFANA_URL, GRAFANA_USER, GRAFANA_PASS)
    auth_handler = urllib.request.HTTPBasicAuthHandler(password_mgr)
    opener = urllib.request.build_opener(auth_handler)

    abs_output = os.path.join(REPO_ROOT, output_path)
    os.makedirs(os.path.dirname(abs_output), exist_ok=True)

    try:
        req = urllib.request.Request(render_url)
        with opener.open(req, timeout=60) as resp:
            data = resp.read()
            with open(abs_output, "wb") as f:
                f.write(data)
            print(f"    {output_path} ({len(data)} bytes)")
            return True
    except Exception as e:
        print(f"    {output_path} FAILED: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--burn-minutes", type=int, default=30,
                        help="How long to run fault injection before capturing (default: 30)")
    parser.add_argument("--inject-rate", type=int, default=5,
                        help="Fault injector request rate (default: 5)")
    parser.add_argument("--error-ratio", type=float, default=0.3,
                        help="Fault injector error ratio (default: 0.3)")
    parser.add_argument("--width", type=int, default=1200, help="Screenshot width (default: 1200)")
    parser.add_argument("--height", type=int, default=600, help="Screenshot height (default: 600)")
    parser.add_argument("--time-range", default="now-1h", help="Dashboard time range (default: now-1h)")
    parser.add_argument("--dry-run", action="store_true", help="Print commands without executing")
    args = parser.parse_args()

    print(f"\n  Observatory Screenshot Capture")
    print(f"  {'='*40}")
    print(f"  Burn duration:  {args.burn_minutes} minutes")
    print(f"  Inject rate:    {args.inject_rate} req/s")
    print(f"  Error ratio:    {args.error_ratio}")
    print(f"  Time range:     {args.time_range}")
    print(f"  Screenshot:     {args.width}x{args.height}")
    print()

    if args.dry_run:
        print("  DRY RUN — commands that would execute:")
        print(f"    1. python {FAULT_INJECTOR} --duration {args.burn_minutes * 60} --rate {args.inject_rate} --error-ratio {args.error_ratio}")
        print(f"    2. sleep {args.burn_minutes * 60}")
        for uid, path in DASHBOARDS:
            print(f"    3. capture {uid} -> {path}")
        print(f"    4. kill fault-injector")
        return 0

    # Step 1: Start fault injector
    print("  Step 1: Starting fault injector...")
    inject_duration = args.burn_minutes * 60 + 300  # extra 5min buffer
    inject_proc = subprocess.Popen(
        [sys.executable, FAULT_INJECTOR,
         "--duration", str(inject_duration),
         "--rate", str(args.inject_rate),
         "--error-ratio", str(args.error_ratio)],
        cwd=REPO_ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    print(f"    PID: {inject_proc.pid}")

    # Step 2: Wait for burn to stabilize
    wait_seconds = args.burn_minutes * 60
    print(f"\n  Step 2: Waiting {args.burn_minutes} minutes for burn to stabilize...")
    try:
        for remaining in range(wait_seconds, 0, -60):
            mins = remaining // 60
            print(f"    {mins}m remaining...", flush=True)
            time.sleep(min(60, remaining))
    except KeyboardInterrupt:
        print("\n  Interrupted!")
        inject_proc.terminate()
        inject_proc.wait(timeout=5)
        return 1

    # Step 3: Capture screenshots WHILE fault injector is still running
    print(f"\n  Step 3: Capturing screenshots (fault injector PID {inject_proc.pid} still running)...")
    if not wait_for_grafana():
        inject_proc.terminate()
        inject_proc.wait(timeout=5)
        return 1

    success = 0
    for uid, path in DASHBOARDS:
        if capture_screenshot(uid, path, args.width, args.height, args.time_range):
            success += 1

    # Step 4: Stop fault injector
    print(f"\n  Step 4: Stopping fault injector (PID {inject_proc.pid})...")
    inject_proc.terminate()
    try:
        inject_proc.wait(timeout=10)
        print("    Stopped cleanly")
    except subprocess.TimeoutExpired:
        inject_proc.kill()
        inject_proc.wait(timeout=5)
        print("    Killed")

    print(f"\n  Done: {success}/{len(DASHBOARDS)} screenshots captured")
    return 0 if success == len(DASHBOARDS) else 1


if __name__ == "__main__":
    sys.exit(main())
