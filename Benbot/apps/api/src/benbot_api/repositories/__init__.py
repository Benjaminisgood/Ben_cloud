from __future__ import annotations

from .bug_reports import (
    clear_archived_bug_reports,
    create_bug_report,
    get_bug_report,
    list_approved_bug_reports,
    list_approved_bug_reports_with_reporter,
    list_archived_bug_reports_with_reporter,
    list_pending_bug_reports_with_reporter,
    save_bug_report,
)
from .metrics import (
    count_users,
    list_bug_report_counts_by_status,
    list_health_rows,
    list_project_log_counts,
)
from .project_stats import (
    get_all_project_total_clicks,
    get_project_health_map,
    get_project_total_clicks,
    increment_project_click,
    list_project_health_rows,
    upsert_project_health,
)
from .project_logs import (
    count_project_logs,
    create_project_log,
    list_project_logs,
    trim_project_logs,
)
from .users import (
    count_active_admins,
    create_user,
    get_user_by_id,
    get_user_by_username,
    has_active_admin,
    list_users,
    update_user_role,
)
from .user_project_access import (
    list_access_rows_for_users,
    list_project_ids_for_user,
    replace_user_project_access,
)

__all__ = [
    "clear_archived_bug_reports",
    "create_bug_report",
    "get_bug_report",
    "save_bug_report",
    "list_pending_bug_reports_with_reporter",
    "list_approved_bug_reports_with_reporter",
    "list_archived_bug_reports_with_reporter",
    "list_approved_bug_reports",
    "increment_project_click",
    "get_project_total_clicks",
    "get_all_project_total_clicks",
    "list_project_health_rows",
    "get_project_health_map",
    "upsert_project_health",
    "list_health_rows",
    "list_project_log_counts",
    "list_bug_report_counts_by_status",
    "count_users",
    "get_user_by_id",
    "get_user_by_username",
    "list_users",
    "create_user",
    "update_user_role",
    "has_active_admin",
    "count_active_admins",
    "list_project_ids_for_user",
    "list_access_rows_for_users",
    "replace_user_project_access",
    "create_project_log",
    "trim_project_logs",
    "list_project_logs",
    "count_project_logs",
]
