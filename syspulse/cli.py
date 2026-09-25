"""Command-line entrypoint.

    python -m syspulse analyze report.json --db health.db
    python -m syspulse show --db health.db --out report.html

Exit codes (useful for Task Scheduler / cron / Jenkins to alert on):
    0 = all checks OK
    1 = at least one WARNING
    2 = at least one CRITICAL
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import report as report_module
from . import storage
from .models import Status
from .rules import evaluate_report, overall_status


def _exit_code_for(status: Status) -> int:
    return {Status.OK: 0, Status.WARNING: 1, Status.CRITICAL: 2}[status]


def cmd_analyze(args: argparse.Namespace) -> int:
    data = json.loads(Path(args.input).read_text())
    results = evaluate_report(data)
    overall = overall_status(results)

    conn = storage.connect(args.db)
    run_id = storage.save_run(conn, data["hostname"], data["collected_at"], overall, results)

    print(f"Run #{run_id} for {data['hostname']}: {overall.value}")
    for r in results:
        print(f"  [{r.status.value:>8}] {r.name}: {r.detail}")

    return _exit_code_for(overall)


def cmd_show(args: argparse.Namespace) -> int:
    conn = storage.connect(args.db)
    run = storage.get_run(conn, args.run_id) if args.run_id else storage.get_latest_run(conn, args.hostname)
    if run is None:
        print("No matching run found.", file=sys.stderr)
        return 2

    results = storage.get_results_for_run(conn, run["id"])
    history = storage.get_history(conn, run["hostname"], limit=args.history)
    html_out = report_module.render_html(run, results, history)

    Path(args.out).write_text(html_out)
    print(f"Wrote {args.out}")
    return _exit_code_for(Status(run["overall"]))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="syspulse")
    sub = parser.add_subparsers(dest="command", required=True)

    p_analyze = sub.add_parser("analyze", help="Evaluate a collector JSON report and store it")
    p_analyze.add_argument("input", help="Path to a collector report (see collectors/collect_windows.ps1)")
    p_analyze.add_argument("--db", default="syspulse.db", help="SQLite database path")
    p_analyze.set_defaults(func=cmd_analyze)

    p_show = sub.add_parser("show", help="Render the latest (or a specific) run as HTML")
    p_show.add_argument("--db", default="syspulse.db", help="SQLite database path")
    p_show.add_argument("--hostname", help="Limit to this host's latest run")
    p_show.add_argument("--run-id", type=int, dest="run_id", help="Render this specific run instead of the latest")
    p_show.add_argument("--history", type=int, default=10, help="How many past runs to list")
    p_show.add_argument("--out", default="report.html", help="Output HTML file path")
    p_show.set_defaults(func=cmd_show)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
