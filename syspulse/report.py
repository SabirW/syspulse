"""Renders a run and its recent history as a single self-contained HTML file."""
from __future__ import annotations

import html
import sqlite3

STATUS_COLORS = {"OK": "#2e7d32", "WARNING": "#b8860b", "CRITICAL": "#c62828"}

_PAGE_TEMPLATE = """<!doctype html>
<html><head><meta charset="utf-8"><title>SysPulse report — {hostname}</title>
<style>
  body {{ font-family: system-ui, sans-serif; max-width: 720px; margin: 32px auto; color: #1c2230; }}
  h1 {{ margin-bottom: 0; }}
  .muted {{ color: #666; margin-top: 4px; }}
  .badge {{ display: inline-block; padding: 2px 10px; border-radius: 99px; color: #fff; font-size: 0.85em; }}
  table {{ border-collapse: collapse; width: 100%; margin-top: 16px; }}
  th, td {{ text-align: left; padding: 6px 8px; border-bottom: 1px solid #e2e5eb; font-size: 0.92em; }}
  th {{ color: #666; font-weight: 600; }}
</style></head>
<body>
  <h1>SysPulse report</h1>
  <p class="muted">{hostname} &middot; collected {collected_at} &middot; overall
    <span class="badge" style="background:{overall_color}">{overall}</span>
  </p>

  <h2>Checks</h2>
  <table>
    <tr><th>Check</th><th>Status</th><th>Detail</th></tr>
    {rows}
  </table>

  <h2>Recent history for {hostname}</h2>
  <table>
    <tr><th>Run</th><th>Collected at</th><th>Overall</th></tr>
    {history_rows}
  </table>
</body></html>
"""


def _badge(status: str) -> str:
    color = STATUS_COLORS.get(status, "#666")
    return f'<span class="badge" style="background:{color}">{html.escape(status)}</span>'


def render_html(run: sqlite3.Row, results: list[sqlite3.Row], history: list[sqlite3.Row]) -> str:
    rows = "\n".join(
        f"<tr><td>{html.escape(r['name'])}</td><td>{_badge(r['status'])}</td>"
        f"<td>{html.escape(r['detail'])}</td></tr>"
        for r in results
    )
    history_rows = "\n".join(
        f"<tr><td>#{h['id']}</td><td>{html.escape(h['collected_at'])}</td>"
        f"<td>{_badge(h['overall'])}</td></tr>"
        for h in history
    )
    return _PAGE_TEMPLATE.format(
        hostname=html.escape(run["hostname"]),
        collected_at=html.escape(run["collected_at"]),
        overall=html.escape(run["overall"]),
        overall_color=STATUS_COLORS.get(run["overall"], "#666"),
        rows=rows or "<tr><td colspan=3>No checks recorded.</td></tr>",
        history_rows=history_rows or "<tr><td colspan=3>No prior runs.</td></tr>",
    )
