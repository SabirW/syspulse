"""Threshold rules: turn a raw collector report into a list of CheckResults.

Kept as plain functions over dicts (not classes) so the rules stay easy to
read, test in isolation, and tune without touching storage or reporting.
"""
from __future__ import annotations

from .models import CheckResult, Status

# Services that are expected to be running. A service configured to start
# automatically but found stopped is treated as CRITICAL: that combination
# is exactly what generates "my printer / VPN / antivirus stopped working"
# tickets.
AUTO_START_STATES = {"Automatic"}

DISK_WARNING_PCT = 20.0
DISK_CRITICAL_PCT = 10.0
MAX_RECENT_ERRORS_OK = 5
MAX_RECENT_ERRORS_WARNING = 15


def evaluate_disks(disks: list[dict]) -> list[CheckResult]:
    results = []
    for disk in disks:
        drive = disk["drive"]
        free_pct = disk["free_pct"]
        if free_pct < DISK_CRITICAL_PCT:
            status = Status.CRITICAL
        elif free_pct < DISK_WARNING_PCT:
            status = Status.WARNING
        else:
            status = Status.OK
        detail = f"{disk['free_gb']} GB free of {disk['total_gb']} GB ({free_pct}%)"
        results.append(CheckResult(name=f"disk:{drive}", status=status, detail=detail))
    return results


def evaluate_services(services: list[dict]) -> list[CheckResult]:
    results = []
    for svc in services:
        name = svc["name"]
        status_text = svc["status"]

        if status_text == "NotFound":
            results.append(CheckResult(
                name=f"service:{name}", status=Status.WARNING,
                detail="service is not installed on this host",
            ))
            continue

        is_running = status_text == "Running"
        should_auto_start = svc.get("start_type") in AUTO_START_STATES

        if not is_running and should_auto_start:
            status = Status.CRITICAL
        elif not is_running:
            status = Status.WARNING
        else:
            status = Status.OK

        detail = f"status={status_text}, start_type={svc.get('start_type')}"
        results.append(CheckResult(name=f"service:{name}", status=status, detail=detail))
    return results


def evaluate_recent_errors(recent_errors: list[dict]) -> list[CheckResult]:
    count = len(recent_errors)
    if count > MAX_RECENT_ERRORS_WARNING:
        status = Status.CRITICAL
    elif count > MAX_RECENT_ERRORS_OK:
        status = Status.WARNING
    else:
        status = Status.OK

    top_sources = _top_sources(recent_errors, limit=3)
    detail = f"{count} error/critical events" + (f" (top sources: {top_sources})" if top_sources else "")
    return [CheckResult(name="event_log:errors", status=status, detail=detail)]


def _top_sources(events: list[dict], limit: int) -> str:
    counts: dict[str, int] = {}
    for event in events:
        source = event.get("source", "unknown")
        counts[source] = counts.get(source, 0) + 1
    ranked = sorted(counts.items(), key=lambda pair: pair[1], reverse=True)[:limit]
    return ", ".join(f"{source} x{n}" for source, n in ranked)


def evaluate_report(report: dict) -> list[CheckResult]:
    """Run every rule against a collector report and return all results."""
    results: list[CheckResult] = []
    results += evaluate_disks(report.get("disks", []))
    results += evaluate_services(report.get("services", []))
    results += evaluate_recent_errors(report.get("recent_errors", []))
    return results


def overall_status(results: list[CheckResult]) -> Status:
    if not results:
        return Status.OK
    return max((r.status for r in results), key=lambda s: s.rank)
