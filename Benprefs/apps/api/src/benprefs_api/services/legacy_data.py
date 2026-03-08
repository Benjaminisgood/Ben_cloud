
from __future__ import annotations

import sqlite3
from pathlib import Path

from ..schemas.dashboard import DashboardSnapshot


def _connect(source_db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(source_db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _scalar(conn: sqlite3.Connection, query: str) -> int | float:
    return conn.execute(query).fetchone()[0]


def _rows(conn: sqlite3.Connection, query: str) -> list[dict[str, str]]:
    rows = []
    for row in conn.execute(query).fetchall():
        rows.append({key: "-" if row[key] in (None, "") else str(row[key]) for key in row.keys()})
    return rows


def get_dashboard_snapshot(source_db_path: Path) -> DashboardSnapshot:
    if not source_db_path.exists():
        return DashboardSnapshot(source="preferences.db", summary=[], collections=[])

    conn = _connect(source_db_path)
    try:
        summary = [
            {"label": "当前偏好", "value": str(_scalar(conn, "SELECT COUNT(*) FROM preference_items WHERE is_current = 1")), "hint": "仍在持续成立的偏好条目"},
            {"label": "正向偏好", "value": str(_scalar(conn, "SELECT COUNT(*) FROM preference_items WHERE is_current = 1 AND is_positive = 1")), "hint": "明确喜欢并持续保持的偏好"},
            {"label": "网站偏好", "value": str(_scalar(conn, "SELECT COUNT(*) FROM website_preferences WHERE is_current = 1")), "hint": "正在使用或仍有态度的网站/平台"},
            {"label": "偏好时间线", "value": str(_scalar(conn, "SELECT COUNT(*) FROM preference_timeline")), "hint": "已记录的偏好变化节点"},
        ]
        collections = [
            {
                "title": "当前偏好条目",
                "subtitle": "偏好强度和标签，适合做 agent 用户画像的稳定层",
                "empty_message": "preferences.db 里还没有当前偏好条目",
                "columns": [
                    {"key": "name", "label": "偏好"},
                    {"key": "direction", "label": "方向"},
                    {"key": "intensity", "label": "强度"},
                    {"key": "tags", "label": "标签"},
                ],
                "rows": _rows(
                    conn,
                    '''
                    SELECT
                        name,
                        CASE WHEN is_positive = 1 THEN '喜欢' ELSE '规避' END AS direction,
                        intensity || '/10' AS intensity,
                        COALESCE(tags, '-') AS tags
                    FROM preference_items
                    WHERE is_current = 1
                    ORDER BY COALESCE(last_updated, updated_at) DESC, id DESC
                    LIMIT 8
                    ''',
                ),
            },
            {
                "title": "网站偏好",
                "subtitle": "把常用网站和平台偏好独立出来，方便做上下文路由",
                "empty_message": "preferences.db 里还没有网站偏好",
                "columns": [
                    {"key": "name", "label": "网站"},
                    {"key": "category", "label": "类别"},
                    {"key": "usage_frequency", "label": "频率"},
                    {"key": "intensity", "label": "偏好强度"},
                ],
                "rows": _rows(
                    conn,
                    '''
                    SELECT
                        name,
                        COALESCE(category, '-') AS category,
                        COALESCE(usage_frequency, '-') AS usage_frequency,
                        intensity || '/10' AS intensity
                    FROM website_preferences
                    WHERE is_current = 1
                    ORDER BY updated_at DESC, id DESC
                    LIMIT 8
                    ''',
                ),
            },
        ]
        return DashboardSnapshot(source="preferences.db", summary=summary, collections=collections)
    finally:
        conn.close()
