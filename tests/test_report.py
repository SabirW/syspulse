from syspulse import storage
from syspulse.report import render_html
from syspulse.rules import evaluate_report, overall_status


def test_render_html_includes_hostname_and_statuses(db_path, sick_report):
    conn = storage.connect(db_path)
    results = evaluate_report(sick_report)
    overall = overall_status(results)
    run_id = storage.save_run(conn, sick_report["hostname"], sick_report["collected_at"], overall, results)

    run = storage.get_run(conn, run_id)
    stored_results = storage.get_results_for_run(conn, run_id)
    history = storage.get_history(conn, sick_report["hostname"])

    page = render_html(run, stored_results, history)

    assert sick_report["hostname"] in page
    assert "CRITICAL" in page
    assert "disk:C:" in page


def test_render_html_escapes_untrusted_detail_text(db_path):
    conn = storage.connect(db_path)
    from syspulse.models import CheckResult, Status
    malicious = CheckResult(name="x", status=Status.OK, detail="<script>alert(1)</script>")
    run_id = storage.save_run(conn, "host-a", "2026-01-01T00:00:00Z", Status.OK, [malicious])

    run = storage.get_run(conn, run_id)
    stored_results = storage.get_results_for_run(conn, run_id)
    page = render_html(run, stored_results, [])

    assert "<script>" not in page
    assert "&lt;script&gt;" in page


def test_render_html_handles_no_history():
    conn = storage.connect(":memory:")
    from syspulse.models import Status
    run_id = storage.save_run(conn, "host-a", "2026-01-01T00:00:00Z", Status.OK, [])
    run = storage.get_run(conn, run_id)
    page = render_html(run, [], [])
    assert "No prior runs" in page
