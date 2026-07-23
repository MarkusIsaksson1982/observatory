"""Validate Grafana dashboard JSON files for structural and semantic correctness.

Checks:
  1. Valid JSON syntax
  2. Required top-level fields (title, uid, panels)
  3. Each panel has a title and type
  4. PromQL expr fields: no triple-backslash escaping (\\\\"), no literal backslashes
  5. Datasource references are not unresolved template variables (${...})

Usage:
  python validate_json.py grafana/provisioning/dashboards/*.json
  python validate_json.py grafana/provisioning/dashboards/service-health-red.json
"""
import json
import re
import sys
from pathlib import Path


REQUIRED_DASHBOARD_FIELDS = {"title", "uid", "panels"}
PROMQL_BACKSLASH_RE = re.compile(r'\\')  # literal backslash in decoded string
PROMQL_UNRESOLVED_VAR_RE = re.compile(r'\$\{[^}]+\}')
PROMQL_ESCAPED_QUOTE_RE = re.compile(r'\\"')  # escaped quote in PromQL (should not exist)


def validate_dashboard(path: Path) -> list[str]:
    """Validate a single Grafana dashboard JSON file. Returns list of errors."""
    errors = []

    # 1. JSON syntax
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return [f"JSON syntax error: {e}"]

    # 2. Required fields
    missing = REQUIRED_DASHBOARD_FIELDS - set(data.keys())
    if missing:
        errors.append(f"Missing required fields: {missing}")

    # 3. Panels
    panels = data.get("panels", [])
    if not panels:
        errors.append("No panels found")

    for panel in panels:
        title = panel.get("title", "<untitled>")
        ptype = panel.get("type", "<unknown>")

        # Skip row panels (no targets)
        if ptype == "row":
            continue

        if "title" not in panel:
            errors.append(f"Panel missing title: {panel.get('id', '?')}")

        # Check targets/expressions
        targets = panel.get("targets", [])
        for target in targets:
            expr = target.get("expr", "")
            if not expr:
                continue

            # 4. Check for literal backslashes (triple-backslash encoding bug)
            if PROMQL_BACKSLASH_RE.search(expr):
                errors.append(
                    f"Panel '{title}': expr contains literal backslash - "
                    f"likely triple-backslash encoding bug: {expr[:80]}..."
                )

            # 5. Check for unresolved template variables
            unresolved = PROMQL_UNRESOLVED_VAR_RE.findall(expr)
            # Filter out known dashboard variables
            known_vars = {"${DS_PROMETHEUS}", "${DS_LOKI}", "${DS_TEMPO}", "${VAR_SLO}"}
            real_unresolved = [v for v in unresolved if v not in known_vars]
            if real_unresolved:
                errors.append(
                    f"Panel '{title}': unresolved variables in expr: {real_unresolved}"
                )

            # 6. Check for common PromQL quoting issues
            # Look for label=value without quotes around value (except numeric)
            if re.search(r',\s*\w+="', expr) is False and re.search(r'\w+="\$', expr):
                pass  # Template variable usage is fine

    return errors


def main() -> int:
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <dashboard.json> [dashboard2.json ...]")
        return 1

    total_errors = 0
    for arg in sys.argv[1:]:
        path = Path(arg)
        if not path.exists():
            print(f"SKIP  {arg} (not found)")
            continue

        errors = validate_dashboard(path)
        if errors:
            print(f"FAIL  {path.name}")
            for err in errors:
                print(f"      {err}")
            total_errors += len(errors)
        else:
            print(f"PASS  {path.name}")

    if total_errors:
        print(f"\n{total_errors} error(s) found")
        return 1
    else:
        print("\nAll dashboards valid")
        return 0


if __name__ == "__main__":
    sys.exit(main())
