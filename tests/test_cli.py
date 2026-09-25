import json

from syspulse.cli import main


def test_analyze_healthy_report_exits_zero(tmp_path, healthy_report):
    report_path = tmp_path / "report.json"
    report_path.write_text(json.dumps(healthy_report))
    db_path = tmp_path / "syspulse.db"

    exit_code = main(["analyze", str(report_path), "--db", str(db_path)])

    assert exit_code == 0
    assert db_path.exists()


def test_analyze_sick_report_exits_two(tmp_path, sick_report):
    report_path = tmp_path / "report.json"
    report_path.write_text(json.dumps(sick_report))
    db_path = tmp_path / "syspulse.db"

    exit_code = main(["analyze", str(report_path), "--db", str(db_path)])

    assert exit_code == 2


def test_show_writes_html_file(tmp_path, healthy_report):
    report_path = tmp_path / "report.json"
    report_path.write_text(json.dumps(healthy_report))
    db_path = tmp_path / "syspulse.db"
    out_path = tmp_path / "out.html"

    main(["analyze", str(report_path), "--db", str(db_path)])
    exit_code = main(["show", "--db", str(db_path), "--out", str(out_path)])

    assert exit_code == 0
    assert out_path.exists()
    assert "WKS-HEALTHY-01" in out_path.read_text()


def test_show_with_no_runs_exits_two(tmp_path):
    db_path = tmp_path / "empty.db"
    exit_code = main(["show", "--db", str(db_path), "--out", str(tmp_path / "out.html")])
    assert exit_code == 2
