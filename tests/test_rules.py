from syspulse.models import Status
from syspulse.rules import (
    evaluate_disks,
    evaluate_recent_errors,
    evaluate_report,
    evaluate_services,
    overall_status,
)


# --- disks -------------------------------------------------------------

def test_disk_with_plenty_of_space_is_ok():
    result = evaluate_disks([{"drive": "C:", "total_gb": 100, "free_gb": 60, "free_pct": 60.0}])
    assert result[0].status == Status.OK


def test_disk_below_warning_threshold():
    result = evaluate_disks([{"drive": "C:", "total_gb": 100, "free_gb": 15, "free_pct": 15.0}])
    assert result[0].status == Status.WARNING


def test_disk_below_critical_threshold():
    result = evaluate_disks([{"drive": "C:", "total_gb": 100, "free_gb": 5, "free_pct": 5.0}])
    assert result[0].status == Status.CRITICAL


def test_disk_detail_includes_numbers():
    result = evaluate_disks([{"drive": "D:", "total_gb": 500, "free_gb": 90, "free_pct": 18.0}])
    assert "90" in result[0].detail and "500" in result[0].detail


# --- services ------------------------------------------------------------

def test_running_autostart_service_is_ok():
    result = evaluate_services([{"name": "Spooler", "status": "Running", "start_type": "Automatic"}])
    assert result[0].status == Status.OK


def test_stopped_autostart_service_is_critical():
    result = evaluate_services([{"name": "Spooler", "status": "Stopped", "start_type": "Automatic"}])
    assert result[0].status == Status.CRITICAL


def test_stopped_manual_service_is_warning_not_critical():
    result = evaluate_services([{"name": "BITS", "status": "Stopped", "start_type": "Manual"}])
    assert result[0].status == Status.WARNING


def test_missing_service_is_warning():
    result = evaluate_services([{"name": "GhostSvc", "status": "NotFound", "start_type": None}])
    assert result[0].status == Status.WARNING
    assert "not installed" in result[0].detail


# --- recent errors ---------------------------------------------------------

def test_no_errors_is_ok():
    assert evaluate_recent_errors([])[0].status == Status.OK


def test_few_errors_still_ok():
    events = [{"source": "X"} for _ in range(5)]
    assert evaluate_recent_errors(events)[0].status == Status.OK


def test_many_errors_is_warning():
    events = [{"source": "X"} for _ in range(10)]
    assert evaluate_recent_errors(events)[0].status == Status.WARNING


def test_flood_of_errors_is_critical():
    events = [{"source": "X"} for _ in range(20)]
    assert evaluate_recent_errors(events)[0].status == Status.CRITICAL


def test_top_sources_reported_in_detail():
    events = [{"source": "Disk"} for _ in range(8)] + [{"source": "App"} for _ in range(2)]
    detail = evaluate_recent_errors(events)[0].detail
    assert "Disk x8" in detail


# --- full report / overall status ------------------------------------------

def test_healthy_report_is_all_ok(healthy_report):
    results = evaluate_report(healthy_report)
    assert overall_status(results) == Status.OK
    assert all(r.status == Status.OK for r in results)


def test_sick_report_is_critical(sick_report):
    results = evaluate_report(sick_report)
    assert overall_status(results) == Status.CRITICAL


def test_sick_report_flags_expected_checks(sick_report):
    results = {r.name: r.status for r in evaluate_report(sick_report)}
    assert results["disk:C:"] == Status.CRITICAL
    assert results["disk:D:"] == Status.WARNING
    assert results["service:Spooler"] == Status.CRITICAL
    assert results["service:BITS"] == Status.WARNING
    assert results["service:GhostSvc"] == Status.WARNING
    assert results["event_log:errors"] == Status.WARNING


def test_overall_status_of_empty_list_is_ok():
    assert overall_status([]) == Status.OK
