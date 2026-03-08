from __future__ import annotations

import sqlite3
from datetime import UTC, date, datetime, timedelta

from benfinance_api.models.finance_record import FinanceRecord
from benfinance_api.services.finance_workspace import build_finance_workspace


def _write_source_db(path) -> None:
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            institution TEXT,
            currency TEXT NOT NULL,
            current_balance REAL NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1
        );

        CREATE TABLE transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_date TEXT NOT NULL,
            description TEXT,
            merchant TEXT,
            payee TEXT,
            type TEXT NOT NULL,
            amount REAL NOT NULL
        );

        CREATE TABLE budgets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            start_date TEXT NOT NULL,
            name TEXT NOT NULL,
            amount REAL NOT NULL
        );

        CREATE TABLE savings_goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            deadline TEXT NOT NULL,
            name TEXT NOT NULL,
            target_amount REAL NOT NULL,
            current_amount REAL NOT NULL,
            is_completed INTEGER NOT NULL DEFAULT 0
        );
        """
    )
    cur.executemany(
        "INSERT INTO accounts (name, institution, currency, current_balance, is_active) VALUES (?, ?, ?, ?, ?)",
        [
            ("招商银行卡", "招商银行", "CNY", 1000, 1),
            ("支付宝", "Alipay", "CNY", 200, 1),
        ],
    )
    cur.executemany(
        "INSERT INTO transactions (transaction_date, description, merchant, payee, type, amount) VALUES (?, ?, ?, ?, ?, ?)",
        [
            (date.today().isoformat(), "工资", None, "公司", "income", 1200),
            (date.today().isoformat(), "房租", None, "房东", "expense", 300),
        ],
    )
    cur.execute(
        "INSERT INTO savings_goals (deadline, name, target_amount, current_amount, is_completed) VALUES (?, ?, ?, ?, ?)",
        ("2026-06-30", "应急金", 5000, 2500, 0),
    )
    conn.commit()
    conn.close()


def _record(**kwargs) -> FinanceRecord:
    now = datetime.now(UTC)
    payload = {
        "record_type": "bill",
        "title": "测试记录",
        "description": "测试描述",
        "category": "general",
        "flow_direction": "outflow",
        "planning_status": "active",
        "risk_level": "medium",
        "review_status": "approved",
        "amount": 100.0,
        "currency": "CNY",
        "account_name": "招商银行卡",
        "counterparty": None,
        "occurred_on": None,
        "due_on": date.today() + timedelta(days=7),
        "next_review_on": None,
        "recurrence_rule": None,
        "follow_up_action": None,
        "agent_note": None,
        "review_note": None,
        "created_by": "benbenbuben",
        "updated_by": "benbenbuben",
        "reviewed_by": "benbenbuben",
        "reviewed_at": now,
        "created_at": now,
        "updated_at": now,
    }
    payload.update(kwargs)
    return FinanceRecord(**payload)


def test_build_finance_workspace_returns_account_level_calculations(tmp_path):
    source_db = tmp_path / "finance.db"
    _write_source_db(source_db)

    records = [
        _record(title="房租", amount=300.0, account_name="招商银行卡", due_on=date.today() + timedelta(days=10)),
        _record(
            title="固定订阅",
            record_type="subscription",
            amount=50.0,
            account_name="支付宝",
            recurrence_rule="monthly",
            due_on=None,
        ),
        _record(
            title="未审核决策",
            record_type="decision",
            amount=999.0,
            account_name="招商银行卡",
            review_status="pending_review",
        ),
    ]

    workspace = build_finance_workspace(source_db, records)
    contexts = {item["key"]: item for item in workspace["account_contexts"]}

    assert workspace["hero_metrics"][1]["value"] == "¥350"
    assert contexts["招商银行卡"]["stats"][0]["value"] == "¥1,000"
    assert contexts["招商银行卡"]["stats"][1]["value"] == "¥300"
    assert contexts["招商银行卡"]["stats"][3]["value"] == "¥700"
    assert contexts["招商银行卡"]["coverage_ratio"] == "3.3x"

    assert contexts["支付宝"]["stats"][0]["value"] == "¥200"
    assert contexts["支付宝"]["stats"][1]["value"] == "¥50"
    assert contexts["支付宝"]["stats"][2]["value"] == "¥50"
    assert contexts["支付宝"]["coverage_ratio"] == "4.0x"
