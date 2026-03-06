"""Operational metrics for Benbot."""
from __future__ import annotations

import threading
import time

from sqlalchemy.orm import Session

from ..repositories import (
    count_users,
    list_bug_report_counts_by_status,
    list_health_rows,
    list_project_log_counts,
)

_counter_lock = threading.Lock()
_counters = {
    "benbot_login_success_total": 0,
    "benbot_login_failure_total": 0,
    "benbot_project_control_success_total": 0,
    "benbot_project_control_failure_total": 0,
    "benbot_api_token_auth_total": 0,
    "benbot_health_check_runs_total": 0,
    "benbot_health_check_failures_total": 0,
}


def inc_counter(name: str, amount: int = 1) -> None:
    with _counter_lock:
        if name in _counters:
            _counters[name] += amount


def snapshot_counters() -> dict[str, int]:
    with _counter_lock:
        return dict(_counters)


def render_prometheus_metrics(db: Session) -> str:
    lines: list[str] = []
    counters = snapshot_counters()

    lines.append("# HELP benbot_build_info Benbot build metadata")
    lines.append("# TYPE benbot_build_info gauge")
    lines.append('benbot_build_info{service="benbot"} 1')

    lines.append("# HELP benbot_runtime_unix_timestamp Runtime scrape time")
    lines.append("# TYPE benbot_runtime_unix_timestamp gauge")
    lines.append(f"benbot_runtime_unix_timestamp {int(time.time())}")

    for key, value in counters.items():
        lines.append(f"# HELP {key} Runtime counter for {key}")
        lines.append(f"# TYPE {key} counter")
        lines.append(f"{key} {value}")

    project_rows = list_health_rows(db)
    lines.append("# HELP benbot_projects_total Number of registered projects with health records")
    lines.append("# TYPE benbot_projects_total gauge")
    lines.append(f"benbot_projects_total {len(project_rows)}")

    lines.append("# HELP benbot_project_up Project health state (1 up / 0 down-or-unknown)")
    lines.append("# TYPE benbot_project_up gauge")
    lines.append("# HELP benbot_project_response_ms Project health response latency in milliseconds")
    lines.append("# TYPE benbot_project_response_ms gauge")
    for row in project_rows:
        up_value = 1 if row.status == "up" else 0
        lines.append(f'benbot_project_up{{project_id="{row.project_id}"}} {up_value}')
        if row.response_ms is not None:
            lines.append(
                f'benbot_project_response_ms{{project_id="{row.project_id}"}} {row.response_ms}'
            )

    logs_by_level = list_project_log_counts(db)
    lines.append("# HELP benbot_project_logs_total Total stored project logs by level")
    lines.append("# TYPE benbot_project_logs_total gauge")
    for project_id, level, count in logs_by_level:
        lines.append(
            f'benbot_project_logs_total{{project_id="{project_id}",level="{level}"}} {count}'
        )

    bug_by_status = list_bug_report_counts_by_status(db)
    lines.append("# HELP benbot_bug_reports_total Bug reports by status")
    lines.append("# TYPE benbot_bug_reports_total gauge")
    for status, count in bug_by_status:
        lines.append(f'benbot_bug_reports_total{{status="{status}"}} {count}')

    user_count = count_users(db)
    lines.append("# HELP benbot_users_total Total user records")
    lines.append("# TYPE benbot_users_total gauge")
    lines.append(f"benbot_users_total {user_count}")

    return "\n".join(lines) + "\n"
