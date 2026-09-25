from syspulse import storage
from syspulse.models import CheckResult, Status
from syspulse.rules import evaluate_report, overall_status


def test_save_and_get_run_round_trip(db_path, healthy_report):
    conn = storage.connect(db_path)
    results = evaluate_report(healthy_report)
    overall = overall_status(results)

    run_id = storage.save_run(
        conn, healthy_report["hostname"], healthy_report["collected_at"], overall, results
    )

    run = storage.get_run(conn, run_id)
    assert run["hostname"] == "WKS-HEALTHY-01"
    assert run["overall"] == "OK"

    stored_results = storage.get_results_for_run(conn, run_id)
    assert len(stored_results) == len(results)


def test_get_latest_run_returns_most_recent(db_path):
    conn = storage.connect(db_path)
    storage.save_run(conn, "host-a", "2026-01-01T00:00:00Z", Status.OK, [])
    second_id = storage.save_run(conn, "host-a", "2026-01-02T00:00:00Z", Status.WARNING, [])

    latest = storage.get_latest_run(conn, "host-a")
    assert latest["id"] == second_id
    assert latest["overall"] == "WARNING"


def test_get_latest_run_filters_by_hostname(db_path):
    conn = storage.connect(db_path)
    storage.save_run(conn, "host-a", "2026-01-01T00:00:00Z", Status.OK, [])
    host_b_id = storage.save_run(conn, "host-b", "2026-01-01T00:00:00Z", Status.CRITICAL, [])

    latest = storage.get_latest_run(conn, "host-b")
    assert latest["id"] == host_b_id


def test_get_history_orders_newest_first(db_path):
    conn = storage.connect(db_path)
    for day in ["01", "02", "03"]:
        storage.save_run(conn, "host-a", f"2026-01-{day}T00:00:00Z", Status.OK, [])

    history = storage.get_history(conn, "host-a", limit=10)
    dates = [row["collected_at"] for row in history]
    assert dates == sorted(dates, reverse=True)


def test_get_history_respects_limit(db_path):
    conn = storage.connect(db_path)
    for i in range(5):
        storage.save_run(conn, "host-a", f"2026-01-0{i+1}T00:00:00Z", Status.OK, [])

    assert len(storage.get_history(conn, "host-a", limit=2)) == 2


def test_check_results_are_deleted_with_their_run(db_path):
    conn = storage.connect(db_path)
    result = CheckResult(name="disk:C:", status=Status.OK, detail="fine")
    run_id = storage.save_run(conn, "host-a", "2026-01-01T00:00:00Z", Status.OK, [result])

    conn.execute("DELETE FROM runs WHERE id = ?", (run_id,))
    conn.commit()

    remaining = conn.execute(
        "SELECT COUNT(*) FROM check_results WHERE run_id = ?", (run_id,)
    ).fetchone()[0]
    assert remaining == 0
