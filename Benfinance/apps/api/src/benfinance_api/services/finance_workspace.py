from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path

from ..models.finance_record import FinanceRecord

_ACTIVE_STATUSES = {"planned", "pending", "active"}
_RISK_WEIGHT = {"low": 8, "medium": 16, "high": 26, "critical": 38}
_STATUS_WEIGHT = {"planned": 8, "pending": 14, "active": 18}
_TYPE_LABELS = {
    "income": "收入",
    "expense": "支出",
    "budget": "预算",
    "savings_goal": "储蓄",
    "debt": "债务",
    "investment": "投资",
    "subscription": "订阅",
    "bill": "账单",
    "tax": "税务",
    "decision": "决策",
}


def _connect(source_db_path: Path) -> sqlite3.Connection | None:
    if not source_db_path.exists():
        return None
    conn = sqlite3.connect(source_db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _format_money(value: float) -> str:
    return f"¥{value:,.0f}"


def _format_ratio(numerator: float, denominator: float) -> str:
    if denominator <= 0:
        return "∞"
    return f"{numerator / denominator:.1f}x"


def _percent(value: float, ceiling: float) -> float:
    if ceiling <= 0:
        return 0.0
    return round(max(6.0, min(value / ceiling * 100, 100.0)), 1) if value > 0 else 0.0


def _days_until(target: date | None, *, today: date) -> int | None:
    if target is None:
        return None
    return (target - today).days


def _account_focus_ids(record: FinanceRecord, *, today: date) -> list[str]:
    focus_ids: set[str] = set()
    due_days = _days_until(record.due_on, today=today)

    if record.flow_direction == "outflow":
        focus_ids.add("buffer")
    if due_days is not None and due_days <= 21:
        focus_ids.add("deadlines")
    if record.record_type in {"savings_goal", "investment"}:
        focus_ids.add("goals")
    if record.record_type == "subscription" or record.recurrence_rule:
        focus_ids.add("subscriptions")

    if not focus_ids:
        focus_ids.add("buffer")
    return sorted(focus_ids)


def _priority_score(record: FinanceRecord, *, today: date) -> float:
    score = float(_RISK_WEIGHT.get(record.risk_level, 10))
    score += float(_STATUS_WEIGHT.get(record.planning_status, 0))
    score += min((record.amount or 0) / 600, 18)

    due_days = _days_until(record.due_on, today=today)
    if due_days is not None:
        if due_days <= 7:
            score += 26
        elif due_days <= 14:
            score += 18
        elif due_days <= 30:
            score += 10

    if record.review_status == "pending_review":
        score += 12
    elif record.review_status == "rejected":
        score += 6

    if record.recurrence_rule:
        score += 8
    return score


def _load_accounts(conn: sqlite3.Connection | None) -> list[dict[str, object]]:
    if conn is None:
        return []
    rows = conn.execute(
        """
        SELECT name, institution, currency, current_balance
        FROM accounts
        WHERE is_active = 1
        ORDER BY current_balance DESC, id DESC
        """
    ).fetchall()
    return [
        {
            "name": str(row["name"]),
            "institution": str(row["institution"] or "-"),
            "currency": str(row["currency"]),
            "balance": float(row["current_balance"] or 0),
        }
        for row in rows
    ]


def _load_goals(conn: sqlite3.Connection | None) -> list[dict[str, object]]:
    if conn is None:
        return []
    rows = conn.execute(
        """
        SELECT deadline, name, target_amount, current_amount
        FROM savings_goals
        WHERE is_completed = 0
        ORDER BY deadline ASC, id ASC
        """
    ).fetchall()
    goals: list[dict[str, object]] = []
    for row in rows:
        target_amount = float(row["target_amount"] or 0)
        current_amount = float(row["current_amount"] or 0)
        gap = max(target_amount - current_amount, 0)
        progress = 0.0 if target_amount <= 0 else min(current_amount / target_amount * 100, 100.0)
        goals.append(
            {
                "deadline": str(row["deadline"]),
                "name": str(row["name"]),
                "target_amount": target_amount,
                "current_amount": current_amount,
                "gap": gap,
                "progress": round(progress, 1),
            }
        )
    return goals


def _load_transaction_window(conn: sqlite3.Connection | None) -> dict[str, float]:
    if conn is None:
        return {"income": 0.0, "outflow": 0.0, "net": 0.0}

    rows = conn.execute(
        """
        SELECT type, amount
        FROM transactions
        WHERE transaction_date >= date('now', '-30 day')
        """
    ).fetchall()
    income = 0.0
    outflow = 0.0
    for row in rows:
        amount = float(row["amount"] or 0)
        if str(row["type"]) == "income":
            income += amount
        else:
            outflow += amount
    return {
        "income": income,
        "outflow": outflow,
        "net": income - outflow,
    }


def _build_focus_panels(
    *,
    total_balance: float,
    near_term_commitment: float,
    recurring_commitment: float,
    free_cash: float,
    due_soon_records: list[FinanceRecord],
    goals: list[dict[str, object]],
    recurring_records: list[FinanceRecord],
) -> list[dict[str, object]]:
    cash_scale = max(total_balance, near_term_commitment, recurring_commitment, max(free_cash, 0), 1.0)
    goals_scale = max((float(goal["target_amount"]) for goal in goals), default=1.0)
    due_scale = max((record.amount or 0 for record in due_soon_records), default=1.0)
    recurring_scale = max((record.amount or 0 for record in recurring_records), default=1.0)

    deadline_tracks = [
        {
            "label": record.title,
            "value": _format_money(record.amount or 0),
            "aux": record.due_on.isoformat() if record.due_on else "待定",
            "width": _percent(record.amount or 0, due_scale),
        }
        for record in due_soon_records[:4]
    ]
    goal_tracks = [
        {
            "label": str(goal["name"]),
            "value": f"{_format_money(float(goal['current_amount']))} / {_format_money(float(goal['target_amount']))}",
            "aux": f"缺口 {_format_money(float(goal['gap']))}",
            "width": round(float(goal["progress"]), 1),
        }
        for goal in goals[:4]
    ]
    recurring_tracks = [
        {
            "label": record.title,
            "value": _format_money(record.amount or 0),
            "aux": record.recurrence_rule or "固定",
            "width": _percent(record.amount or 0, recurring_scale),
        }
        for record in recurring_records[:4]
    ]

    return [
        {
            "id": "buffer",
            "label": "现金缓冲",
            "headline": _format_money(free_cash),
            "caption": "可动用余额 - 30天承诺",
            "stats": [
                {"label": "总余额", "value": _format_money(total_balance)},
                {"label": "30天承诺", "value": _format_money(near_term_commitment)},
                {"label": "固定月费", "value": _format_money(recurring_commitment)},
            ],
            "tracks": [
                {
                    "label": "总余额",
                    "value": _format_money(total_balance),
                    "aux": "活跃账户",
                    "width": _percent(total_balance, cash_scale),
                },
                {
                    "label": "30天承诺",
                    "value": _format_money(near_term_commitment),
                    "aux": "近30天要处理",
                    "width": _percent(near_term_commitment, cash_scale),
                },
                {
                    "label": "固定月费",
                    "value": _format_money(recurring_commitment),
                    "aux": "循环支出",
                    "width": _percent(recurring_commitment, cash_scale),
                },
                {
                    "label": "安全垫",
                    "value": _format_money(max(free_cash, 0)),
                    "aux": "剩余缓冲",
                    "width": _percent(max(free_cash, 0), cash_scale),
                },
            ],
        },
        {
            "id": "deadlines",
            "label": "到期窗口",
            "headline": _format_money(sum(record.amount or 0 for record in due_soon_records[:4])),
            "caption": "14天内最该先看的款项",
            "stats": [
                {"label": "14天内", "value": str(len(due_soon_records[:4]))},
                {"label": "最高风险", "value": due_soon_records[0].title if due_soon_records else "-"},
                {"label": "最近到期", "value": due_soon_records[0].due_on.isoformat() if due_soon_records and due_soon_records[0].due_on else "-"},
            ],
            "tracks": deadline_tracks,
        },
        {
            "id": "goals",
            "label": "目标缺口",
            "headline": _format_money(sum(float(goal["gap"]) for goal in goals)),
            "caption": "储蓄目标与补足进度",
            "stats": [
                {"label": "目标数", "value": str(len(goals))},
                {"label": "最近截止", "value": str(goals[0]["deadline"]) if goals else "-"},
                {"label": "最大缺口", "value": _format_money(max((float(goal["gap"]) for goal in goals), default=0))},
            ],
            "tracks": goal_tracks if goal_tracks else [
                {
                    "label": "暂无目标",
                    "value": _format_money(0),
                    "aux": "-",
                    "width": _percent(0, goals_scale),
                }
            ],
        },
        {
            "id": "subscriptions",
            "label": "固定承诺",
            "headline": _format_money(recurring_commitment),
            "caption": "循环支出与订阅负担",
            "stats": [
                {"label": "固定项", "value": str(len(recurring_records))},
                {"label": "月度总额", "value": _format_money(recurring_commitment)},
                {"label": "最大单项", "value": _format_money(max((record.amount or 0 for record in recurring_records), default=0))},
            ],
            "tracks": recurring_tracks if recurring_tracks else [
                {
                    "label": "暂无固定项",
                    "value": _format_money(0),
                    "aux": "-",
                    "width": _percent(0, recurring_scale),
                }
            ],
        },
    ]


def _build_account_context(
    *,
    key: str,
    title: str,
    institution: str,
    balance: float,
    approved_records: list[FinanceRecord],
    today: date,
) -> dict[str, object]:
    near_term_records = [
        record
        for record in approved_records
        if record.flow_direction == "outflow"
        and (
            record.recurrence_rule is not None
            or ((days := _days_until(record.due_on, today=today)) is not None and days <= 30)
        )
    ]
    recurring_records = [
        record
        for record in approved_records
        if record.recurrence_rule is not None or record.record_type in {"subscription", "bill"}
    ]
    goal_records = [
        record
        for record in approved_records
        if record.record_type in {"savings_goal", "investment"}
    ]
    deadline_records = sorted(
        [
            record
            for record in approved_records
            if (days := _days_until(record.due_on, today=today)) is not None and days <= 30
        ],
        key=lambda record: (record.due_on or date.max, -(record.amount or 0)),
    )

    near_term_commitment = sum(record.amount or 0 for record in near_term_records)
    recurring_commitment = sum(record.amount or 0 for record in recurring_records)
    goal_commitment = sum(record.amount or 0 for record in goal_records)
    free_cash = balance - near_term_commitment

    track_scale = max(balance, near_term_commitment, recurring_commitment, goal_commitment, max(free_cash, 0), 1.0)
    highlights = [
        {
            "title": record.title,
            "value": _format_money(record.amount or 0),
            "aux": record.due_on.isoformat() if record.due_on else (record.recurrence_rule or "待定"),
        }
        for record in deadline_records[:3]
    ]

    return {
        "key": key,
        "title": title,
        "institution": institution,
        "balance_label": _format_money(balance),
        "coverage_ratio": _format_ratio(balance, near_term_commitment),
        "stats": [
            {"label": "余额", "value": _format_money(balance)},
            {"label": "30天承诺", "value": _format_money(near_term_commitment)},
            {"label": "固定承诺", "value": _format_money(recurring_commitment)},
            {"label": "安全垫", "value": _format_money(free_cash)},
        ],
        "tracks": [
            {
                "label": "到期事项",
                "value": _format_money(sum(record.amount or 0 for record in deadline_records)),
                "aux": f"{len(deadline_records)} 条",
                "width": _percent(sum(record.amount or 0 for record in deadline_records), track_scale),
            },
            {
                "label": "固定承诺",
                "value": _format_money(recurring_commitment),
                "aux": f"{len(recurring_records)} 条",
                "width": _percent(recurring_commitment, track_scale),
            },
            {
                "label": "目标投入",
                "value": _format_money(goal_commitment),
                "aux": f"{len(goal_records)} 条",
                "width": _percent(goal_commitment, track_scale),
            },
        ],
        "highlights": highlights,
    }


def build_finance_workspace(source_db_path: Path, finance_records: list[FinanceRecord]) -> dict[str, object]:
    today = date.today()
    conn = _connect(source_db_path)

    try:
        accounts = _load_accounts(conn)
        goals = _load_goals(conn)
        transaction_window = _load_transaction_window(conn)
    finally:
        if conn is not None:
            conn.close()

    total_balance = sum(float(account["balance"]) for account in accounts)
    account_scale = max((float(account["balance"]) for account in accounts), default=1.0)
    account_distribution = [
        {
            "name": str(account["name"]),
            "institution": str(account["institution"]),
            "value": _format_money(float(account["balance"])),
            "share": _percent(float(account["balance"]), total_balance or 1.0),
            "width": _percent(float(account["balance"]), account_scale),
        }
        for account in accounts[:4]
    ]

    approved_actionable = [
        record
        for record in finance_records
        if record.review_status == "approved" and record.planning_status in _ACTIVE_STATUSES
    ]
    due_soon_records = sorted(
        [
            record
            for record in approved_actionable
            if (days := _days_until(record.due_on, today=today)) is not None and days <= 14
        ],
        key=lambda record: (record.due_on or date.max, -(record.amount or 0)),
    )
    near_term_records = [
        record
        for record in approved_actionable
        if record.flow_direction == "outflow"
        and (
            record.recurrence_rule is not None
            or ((days := _days_until(record.due_on, today=today)) is not None and days <= 30)
        )
    ]
    recurring_records = [
        record
        for record in approved_actionable
        if record.recurrence_rule is not None or record.record_type in {"subscription", "bill"}
    ]

    near_term_commitment = sum(record.amount or 0 for record in near_term_records)
    recurring_commitment = sum(record.amount or 0 for record in recurring_records)
    goal_gap = sum(float(goal["gap"]) for goal in goals)
    free_cash = total_balance - near_term_commitment

    hero_metrics = [
        {
            "label": "可动用余额",
            "value": _format_money(total_balance),
            "hint": "活跃账户总额",
            "tone": "cash",
        },
        {
            "label": "30天承诺",
            "value": _format_money(near_term_commitment),
            "hint": "审核通过且待处理",
            "tone": "outflow",
        },
        {
            "label": "目标缺口",
            "value": _format_money(goal_gap),
            "hint": "储蓄目标未补足",
            "tone": "goal",
        },
        {
            "label": "近30天净流入",
            "value": _format_money(transaction_window["net"]),
            "hint": "finance.db 流入减流出",
            "tone": "net" if transaction_window["net"] >= 0 else "warn",
        },
    ]

    focus_panels = _build_focus_panels(
        total_balance=total_balance,
        near_term_commitment=near_term_commitment,
        recurring_commitment=recurring_commitment,
        free_cash=free_cash,
        due_soon_records=due_soon_records,
        goals=goals,
        recurring_records=recurring_records,
    )

    sorted_records = sorted(
        finance_records,
        key=lambda record: (_priority_score(record, today=today), record.updated_at.timestamp()),
        reverse=True,
    )
    priority_cards = []
    for record in sorted_records[:6]:
        focus_ids = _account_focus_ids(record, today=today)
        due_days = _days_until(record.due_on, today=today)
        priority_cards.append(
            {
                "id": record.id,
                "title": record.title,
                "type_label": _TYPE_LABELS.get(record.record_type, record.record_type),
                "status_label": record.planning_status,
                "risk_label": record.risk_level,
                "review_label": record.review_status,
                "amount_label": f"{record.currency} {record.amount:,.0f}" if record.amount is not None else f"{record.currency} --",
                "due_label": record.due_on.isoformat() if record.due_on else "待定",
                "due_hint": (
                    f"{due_days} 天内"
                    if due_days is not None and due_days >= 0
                    else ("已逾期" if due_days is not None else "无日期")
                ),
                "account_name": record.account_name or "",
                "counterparty": record.counterparty or "",
                "category": record.category,
                "recurrence_rule": record.recurrence_rule or "",
                "description": record.description,
                "follow_up_action": record.follow_up_action or "",
                "review_note": record.review_note or "",
                "focus_ids": focus_ids,
                "focus_attr": " ".join(focus_ids),
            }
        )

    approved_by_account: dict[str, list[FinanceRecord]] = {}
    for record in approved_actionable:
        account_key = (record.account_name or "").strip()
        if not account_key:
            continue
        approved_by_account.setdefault(account_key, []).append(record)

    account_contexts = [
        _build_account_context(
            key="",
            title="全部账户",
            institution="组合视角",
            balance=total_balance,
            approved_records=approved_actionable,
            today=today,
        )
    ]
    for account in accounts[:4]:
        name = str(account["name"])
        account_contexts.append(
            _build_account_context(
                key=name,
                title=name,
                institution=str(account["institution"]),
                balance=float(account["balance"]),
                approved_records=approved_by_account.get(name, []),
                today=today,
            )
        )

    return {
        "hero_metrics": hero_metrics,
        "account_distribution": account_distribution,
        "account_contexts": account_contexts,
        "focus_panels": focus_panels,
        "priority_cards": priority_cards,
        "coverage_ratio": _format_ratio(total_balance, near_term_commitment),
        "free_cash_label": _format_money(free_cash),
    }
