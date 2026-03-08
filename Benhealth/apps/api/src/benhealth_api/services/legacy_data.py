
from __future__ import annotations

import sqlite3
from pathlib import Path

from ..schemas.dashboard import DashboardSnapshot


def _connect(source_db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(source_db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _scalar(conn: sqlite3.Connection, query: str) -> int | float:
    value = conn.execute(query).fetchone()[0]
    return value or 0


def _rows(conn: sqlite3.Connection, query: str) -> list[dict[str, str]]:
    rows = []
    for row in conn.execute(query).fetchall():
        rows.append({key: "-" if row[key] in (None, "") else str(row[key]) for key in row.keys()})
    return rows


def get_dashboard_snapshot(source_db_path: Path) -> DashboardSnapshot:
    if not source_db_path.exists():
        return DashboardSnapshot(source="health.db", summary=[], collections=[])

    conn = _connect(source_db_path)
    try:
        total_minutes = _scalar(conn, "SELECT COALESCE(SUM(duration_minutes), 0) FROM workouts")
        summary = [
            {"label": "运动记录", "value": str(_scalar(conn, "SELECT COUNT(*) FROM workouts")), "hint": "累计运动次数"},
            {"label": "总时长", "value": f"{int(total_minutes)} 分钟", "hint": "已记录的运动总时长"},
            {"label": "营养日", "value": str(_scalar(conn, "SELECT COUNT(*) FROM daily_nutrition_summary")), "hint": "有营养汇总的日期数"},
            {"label": "健康目标", "value": str(_scalar(conn, "SELECT COUNT(*) FROM health_goals WHERE status = 'active'")), "hint": "仍在推进的健康目标"},
        ]
        collections = [
            {
                "title": "最近运动",
                "subtitle": "把强度、时长和状态变化放在同一张表里",
                "empty_message": "health.db 里还没有运动记录",
                "columns": [
                    {"key": "start_time", "label": "开始时间"},
                    {"key": "duration_minutes", "label": "时长"},
                    {"key": "intensity", "label": "强度"},
                    {"key": "post_workout_mood", "label": "结束状态"},
                ],
                "rows": _rows(
                    conn,
                    '''
                    SELECT
                        start_time,
                        duration_minutes || ' 分钟' AS duration_minutes,
                        COALESCE(intensity, '-') AS intensity,
                        COALESCE(post_workout_mood, '-') AS post_workout_mood
                    FROM workouts
                    ORDER BY start_time DESC, id DESC
                    LIMIT 8
                    ''',
                ),
            },
            {
                "title": "身体指标与营养",
                "subtitle": "最近一次身体指标，加上最近营养汇总",
                "empty_message": "health.db 里还没有身体指标或营养汇总",
                "columns": [
                    {"key": "date", "label": "日期"},
                    {"key": "weight", "label": "体重/BMI"},
                    {"key": "cardio", "label": "静息心率/饮水"},
                    {"key": "energy", "label": "热量/蛋白质"},
                ],
                "rows": _rows(
                    conn,
                    '''
                    SELECT
                        COALESCE(strftime('%Y-%m-%d', recorded_at), date) AS date,
                        CASE
                            WHEN weight IS NOT NULL THEN printf('%.1fkg / BMI %.1f', weight, bmi)
                            ELSE '-'
                        END AS weight,
                        CASE
                            WHEN resting_heart_rate IS NOT NULL THEN resting_heart_rate || ' bpm'
                            ELSE water_ml || ' ml'
                        END AS cardio,
                        CASE
                            WHEN total_calories IS NOT NULL THEN printf('%.0fkcal / %.1fg', total_calories, total_protein)
                            ELSE '-'
                        END AS energy
                    FROM (
                        SELECT recorded_at, weight, bmi, resting_heart_rate, NULL AS date, NULL AS total_calories, NULL AS total_protein, NULL AS water_ml
                        FROM body_metrics
                        UNION ALL
                        SELECT NULL AS recorded_at, NULL AS weight, NULL AS bmi, NULL AS resting_heart_rate, date, total_calories, total_protein, water_ml
                        FROM daily_nutrition_summary
                    )
                    ORDER BY date DESC, recorded_at DESC
                    LIMIT 8
                    ''',
                ),
            },
        ]
        return DashboardSnapshot(source="health.db", summary=summary, collections=collections)
    finally:
        conn.close()
