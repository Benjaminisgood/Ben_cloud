
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
        return DashboardSnapshot(source="finance.db", summary=[], collections=[])

    conn = _connect(source_db_path)
    try:
        total_balance = _scalar(conn, "SELECT COALESCE(SUM(current_balance), 0) FROM accounts WHERE is_active = 1")
        summary = [
            {"label": "活跃账户", "value": str(_scalar(conn, "SELECT COUNT(*) FROM accounts WHERE is_active = 1")), "hint": "当前仍在使用的账户数"},
            {"label": "总余额", "value": f"¥{total_balance:,.2f}", "hint": "账户 current_balance 汇总"},
            {"label": "交易流水", "value": str(_scalar(conn, "SELECT COUNT(*) FROM transactions")), "hint": "已记录的交易总数"},
            {"label": "储蓄目标", "value": str(_scalar(conn, "SELECT COUNT(*) FROM savings_goals WHERE is_completed = 0")), "hint": "仍在进行中的储蓄目标"},
        ]
        collections = [
            {
                "title": "账户概览",
                "subtitle": "先看资金分布，再看流水和预算",
                "empty_message": "finance.db 里还没有账户",
                "columns": [
                    {"key": "name", "label": "账户"},
                    {"key": "institution", "label": "机构"},
                    {"key": "currency", "label": "币种"},
                    {"key": "current_balance", "label": "余额"},
                ],
                "rows": _rows(
                    conn,
                    '''
                    SELECT
                        name,
                        COALESCE(institution, '-') AS institution,
                        currency,
                        printf('¥%.2f', current_balance) AS current_balance
                    FROM accounts
                    WHERE is_active = 1
                    ORDER BY current_balance DESC, id DESC
                    LIMIT 8
                    ''',
                ),
            },
            {
                "title": "最近交易与预算",
                "subtitle": "让近期支出、预算和目标在一个视图里对齐",
                "empty_message": "finance.db 里还没有交易、预算或储蓄目标",
                "columns": [
                    {"key": "date", "label": "日期"},
                    {"key": "name", "label": "条目"},
                    {"key": "type", "label": "类型"},
                    {"key": "amount", "label": "金额"},
                ],
                "rows": _rows(
                    conn,
                    '''
                    SELECT
                        transaction_date AS date,
                        COALESCE(description, merchant, payee, '交易记录') AS name,
                        type,
                        printf('¥%.2f', amount) AS amount
                    FROM transactions
                    UNION ALL
                    SELECT
                        start_date AS date,
                        name,
                        'budget' AS type,
                        printf('¥%.2f', amount) AS amount
                    FROM budgets
                    UNION ALL
                    SELECT
                        deadline AS date,
                        name,
                        'goal' AS type,
                        printf('¥%.2f / 已有 %.2f', target_amount, current_amount) AS amount
                    FROM savings_goals
                    ORDER BY date DESC
                    LIMIT 8
                    ''',
                ),
            },
        ]
        return DashboardSnapshot(source="finance.db", summary=summary, collections=collections)
    finally:
        conn.close()
