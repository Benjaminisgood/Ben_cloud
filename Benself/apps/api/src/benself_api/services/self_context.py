from __future__ import annotations

import importlib.util
import os
import sqlite3
from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from pathlib import Path

from benself_api.core.config import Settings
from benself_api.schemas.dashboard import (
    AgentContextPreview,
    ConfirmedFact,
    ConfirmedFactDomain,
    DashboardMetric,
    DashboardSnapshot,
    GraphitiStatus,
    RawJournalFact,
)


@dataclass(frozen=True)
class PreparedEpisode:
    name: str
    body: str
    source_description: str
    reference_time: datetime


@dataclass(frozen=True)
class ContextBundle:
    snapshot: DashboardSnapshot
    raw_episodes: list[PreparedEpisode]
    confirmed_episodes: list[PreparedEpisode]


def _connect(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def _safe_text(value: object | None, fallback: str = "-") -> str:
    if value is None:
        return fallback
    text = str(value).strip()
    return text or fallback


def _parse_date_reference(value: str | None) -> datetime:
    if not value:
        return datetime.now(UTC)
    parsed = date.fromisoformat(value[:10])
    return datetime.combine(parsed, time.min, tzinfo=UTC)


def _graphiti_status(settings: Settings) -> GraphitiStatus:
    package_available = importlib.util.find_spec("graphiti_core") is not None
    api_key_present = bool(os.environ.get("OPENAI_API_KEY"))
    enabled = settings.GRAPHITI_ENABLED
    ready = enabled and package_available and api_key_present

    if not enabled:
        hint = "Graphiti 已关闭，当前只生成可复制给 AI 的结构化上下文。"
        backend = "disabled"
    elif not package_available:
        hint = "Graphiti 依赖未安装，先运行 `make install` 后再同步。"
        backend = "missing-package"
    elif not api_key_present:
        hint = "已接好 Graphiti 与本地 Kuzu，补充 `OPENAI_API_KEY` 后即可执行同步和搜索。"
        backend = "graphiti+kuzu"
    else:
        hint = f"Graphiti 已就绪，图数据库落在 {settings.GRAPHITI_KUZU_DB_PATH}。"
        backend = "graphiti+kuzu"

    return GraphitiStatus(enabled=enabled, ready=ready, backend=backend, sync_hint=hint)


def _load_raw_journals(path: Path, *, limit: int) -> list[RawJournalFact]:
    if not path.exists():
        return []

    conn = _connect(path)
    try:
        rows = conn.execute(
            """
            SELECT
                d.id,
                d.date,
                COALESCE(d.title, '未命名 journal') AS title,
                COALESCE(m.name, '未标记情绪') AS mood_name,
                d.current_state,
                d.thoughts,
                d.focus_areas,
                d.tags,
                d.word_count
            FROM daily_records AS d
            LEFT JOIN mood_tags AS m ON m.id = d.mood_primary_id
            ORDER BY d.date DESC, d.id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [
            RawJournalFact(
                id=int(row["id"]),
                date=_safe_text(row["date"]),
                title=_safe_text(row["title"]),
                mood=_safe_text(row["mood_name"]),
                current_state=_safe_text(row["current_state"]),
                thoughts=_safe_text(row["thoughts"]),
                focus_areas=_safe_text(row["focus_areas"]),
                tags=_safe_text(row["tags"]),
                word_count=int(row["word_count"] or 0),
            )
            for row in rows
        ]
    finally:
        conn.close()


def _load_preferences(path: Path) -> ConfirmedFactDomain:
    if not path.exists():
        return ConfirmedFactDomain(id="preferences", icon="💛", title="Preferences", subtitle="没有找到 preferences.db", facts=[])

    conn = _connect(path)
    try:
        facts: list[ConfirmedFact] = []
        for row in conn.execute(
            """
            SELECT id, name, is_positive, intensity, tags, notes, COALESCE(last_updated, updated_at) AS fact_date
            FROM preference_items
            WHERE is_current = 1
            ORDER BY COALESCE(last_updated, updated_at) DESC, id DESC
            LIMIT 4
            """
        ).fetchall():
            direction = "喜欢" if row["is_positive"] else "规避"
            facts.append(
                ConfirmedFact(
                    title=f"{direction} {row['name']}",
                    detail=f"强度 {row['intensity']}/10；标签 {_safe_text(row['tags'])}；备注 {_safe_text(row['notes'])}",
                    fact_date=_safe_text(row["fact_date"]),
                    source_label="preferences.db / preference_items",
                )
            )
        for row in conn.execute(
            """
            SELECT id, name, category, usage_frequency, intensity, updated_at
            FROM website_preferences
            WHERE is_current = 1
            ORDER BY updated_at DESC, id DESC
            LIMIT 2
            """
        ).fetchall():
            facts.append(
                ConfirmedFact(
                    title=f"常用站点 {row['name']}",
                    detail=f"类别 {_safe_text(row['category'])}；频率 {_safe_text(row['usage_frequency'])}；偏好强度 {row['intensity']}/10",
                    fact_date=_safe_text(row["updated_at"])[:10],
                    source_label="preferences.db / website_preferences",
                )
            )
    finally:
        conn.close()

    return ConfirmedFactDomain(
        id="preferences",
        icon="💛",
        title="Preferences",
        subtitle="来自 Benprefs 的稳定喜恶和平台偏好，可视为长期画像层。",
        facts=facts,
    )


def _load_health(path: Path) -> ConfirmedFactDomain:
    if not path.exists():
        return ConfirmedFactDomain(id="health", icon="🌿", title="Health", subtitle="没有找到 health.db", facts=[])

    conn = _connect(path)
    try:
        facts: list[ConfirmedFact] = []
        for row in conn.execute(
            """
            SELECT
                COALESCE(t.name, '训练') AS workout_name,
                DATE(w.start_time) AS fact_date,
                w.duration_minutes,
                w.intensity,
                w.distance_km,
                w.post_workout_mood,
                w.notes
            FROM workouts AS w
            LEFT JOIN workout_types AS t ON t.id = w.workout_type_id
            ORDER BY w.start_time DESC, w.id DESC
            LIMIT 3
            """
        ).fetchall():
            distance = f"{row['distance_km']} km" if row["distance_km"] is not None else "未记录距离"
            facts.append(
                ConfirmedFact(
                    title=f"训练 {row['workout_name']}",
                    detail=(
                        f"{row['duration_minutes']} 分钟；强度 {row['intensity']}/5；{distance}；"
                        f"训练后状态 {_safe_text(row['post_workout_mood'])}；备注 {_safe_text(row['notes'])}"
                    ),
                    fact_date=_safe_text(row["fact_date"]),
                    source_label="health.db / workouts",
                )
            )
        latest_metric = conn.execute(
            """
            SELECT recorded_at, weight, bmi, body_fat_percentage, resting_heart_rate
            FROM body_metrics
            ORDER BY recorded_at DESC, id DESC
            LIMIT 1
            """
        ).fetchone()
        if latest_metric:
            facts.append(
                ConfirmedFact(
                    title="最新体征快照",
                    detail=(
                        f"体重 {_safe_text(latest_metric['weight'])} kg；BMI {_safe_text(latest_metric['bmi'])}；"
                        f"体脂 {_safe_text(latest_metric['body_fat_percentage'])}%；静息心率 {_safe_text(latest_metric['resting_heart_rate'])}"
                    ),
                    fact_date=_safe_text(latest_metric["recorded_at"])[:10],
                    source_label="health.db / body_metrics",
                )
            )
    finally:
        conn.close()

    return ConfirmedFactDomain(
        id="health",
        icon="🌿",
        title="Health",
        subtitle="来自 Benhealth 的运动与体征记录，可视为身体状态的确认层。",
        facts=facts,
    )


def _load_finance(path: Path) -> ConfirmedFactDomain:
    if not path.exists():
        return ConfirmedFactDomain(id="finance", icon="💸", title="Finance", subtitle="没有找到 finance.db", facts=[])

    conn = _connect(path)
    try:
        facts: list[ConfirmedFact] = []
        for row in conn.execute(
            """
            SELECT type, amount, transaction_date, description, merchant, notes
            FROM transactions
            ORDER BY transaction_date DESC, id DESC
            LIMIT 4
            """
        ).fetchall():
            label = "收入" if row["type"] == "income" else "支出"
            detail = _safe_text(row["description"], fallback=_safe_text(row["notes"], fallback=_safe_text(row["merchant"])))
            facts.append(
                ConfirmedFact(
                    title=f"{label} {row['amount']} 元",
                    detail=f"{detail}；商户 {_safe_text(row['merchant'])}；备注 {_safe_text(row['notes'])}",
                    fact_date=_safe_text(row["transaction_date"]),
                    source_label="finance.db / transactions",
                )
            )
        for row in conn.execute(
            """
            SELECT name, amount, period, start_date, end_date
            FROM budgets
            WHERE is_active = 1
            ORDER BY id DESC
            LIMIT 2
            """
        ).fetchall():
            facts.append(
                ConfirmedFact(
                    title=f"预算 {row['name']}",
                    detail=f"{row['period']} 额度 {row['amount']} 元；周期 {row['start_date']} 到 {_safe_text(row['end_date'])}",
                    fact_date=_safe_text(row["start_date"]),
                    source_label="finance.db / budgets",
                )
            )
    finally:
        conn.close()

    return ConfirmedFactDomain(
        id="finance",
        icon="💸",
        title="Finance",
        subtitle="来自 Benfinance 的消费与预算记录，可视为决策偏好与现实约束层。",
        facts=facts,
    )


def _build_agent_context(raw_journals: list[RawJournalFact], confirmed_domains: list[ConfirmedFactDomain]) -> AgentContextPreview:
    latest = raw_journals[:2]
    confirmed_lines = [
        f"[{domain.title}] {fact.title}：{fact.detail}"
        for domain in confirmed_domains
        for fact in domain.facts[:3]
    ]
    recent_lines = [
        f"{item.date}：当前状态 {item.current_state}；想法 {item.thoughts}；关注 {item.focus_areas}"
        for item in latest
    ]
    profile_lines = []
    for domain in confirmed_domains:
        if domain.facts:
            profile_lines.append(f"{domain.title}: {domain.facts[0].title}")

    prompt_block = "\n".join(
        [
            "你是服务 Ben 的 AI 助手。",
            "优先级规则：确认事实 > 原始 journal。",
            "确认事实来自 preferences / health / finance，默认视为已确认。",
            "journal 是阶段性自述，引用时必须带上日期并承认其主观性。",
            "",
            "当前确认事实：",
            *[f"- {line}" for line in confirmed_lines[:9]],
            "",
            "最近 raw journal：",
            *[f"- {line}" for line in recent_lines],
            "",
            "与你互动时请优先：",
            "- 给出贴合偏好与体能状态的建议。",
            "- 涉及金钱与健康时，用确认事实约束建议。",
            "- 如果 journal 和确认事实冲突，先指出冲突，再向 Ben 求证。",
        ]
    )

    narrative = "；".join(profile_lines + recent_lines[:1]) if (profile_lines or recent_lines) else "暂无足够数据生成自我画像。"
    return AgentContextPreview(
        narrative=narrative,
        confirmed_facts=confirmed_lines[:9],
        recent_signals=recent_lines,
        suggested_prompts=[
            "根据确认事实和最近 journal，给 Ben 一份今天的行动建议。",
            "识别最近 journal 中的高风险信号，并说明哪些已经被确认事实支持。",
            "把当前偏好、健康、财务限制整理成 AI 协作前置说明。",
        ],
        prompt_block=prompt_block,
    )


def build_dashboard_snapshot(settings: Settings) -> DashboardSnapshot:
    raw_journals = _load_raw_journals(settings.JOURNALS_DATABASE_PATH, limit=settings.GRAPHITI_MAX_RAW_EPISODES)
    confirmed_domains = [
        _load_preferences(settings.PREFERENCES_DATABASE_PATH),
        _load_health(settings.HEALTH_DATABASE_PATH),
        _load_finance(settings.FINANCE_DATABASE_PATH),
    ]
    confirmed_count = sum(len(domain.facts) for domain in confirmed_domains)
    graphiti = _graphiti_status(settings)
    summary = [
        DashboardMetric(label="Raw Journals", value=str(len(raw_journals)), hint="最近可作为原始事实源的 daily records 数量"),
        DashboardMetric(label="Confirmed Facts", value=str(confirmed_count), hint="来自 Preferences / Health / Finance 的确认事实总数"),
        DashboardMetric(label="Connected Domains", value=str(len([domain for domain in confirmed_domains if domain.facts])), hint="当前已接入并有数据的确认域"),
        DashboardMetric(label="Graphiti", value="Ready" if graphiti.ready else "Pending", hint=graphiti.sync_hint),
    ]
    return DashboardSnapshot(
        summary=summary,
        raw_journals=raw_journals,
        confirmed_domains=confirmed_domains,
        agent_context=_build_agent_context(raw_journals, confirmed_domains),
        graphiti=graphiti,
    )


def build_context_bundle(settings: Settings) -> ContextBundle:
    snapshot = build_dashboard_snapshot(settings)
    raw_episodes = [
        PreparedEpisode(
            name=f"journal-{item.date}-{item.id}",
            body="\n".join(
                [
                    f"date: {item.date}",
                    f"title: {item.title}",
                    f"mood: {item.mood}",
                    f"current_state: {item.current_state}",
                    f"thoughts: {item.thoughts}",
                    f"focus_areas: {item.focus_areas}",
                    f"tags: {item.tags}",
                ]
            ),
            source_description="raw journal from journals.db daily_records",
            reference_time=_parse_date_reference(item.date),
        )
        for item in snapshot.raw_journals
    ]
    confirmed_episodes: list[PreparedEpisode] = []
    for domain in snapshot.confirmed_domains:
        for index, fact in enumerate(domain.facts):
            confirmed_episodes.append(
                PreparedEpisode(
                    name=f"confirmed-{domain.id}-{index + 1}",
                    body="\n".join(
                        [
                            f"domain: {domain.title}",
                            f"title: {fact.title}",
                            f"detail: {fact.detail}",
                            f"source: {fact.source_label}",
                        ]
                    ),
                    source_description=f"confirmed fact from {fact.source_label}",
                    reference_time=_parse_date_reference(fact.fact_date),
                )
            )
    return ContextBundle(
        snapshot=snapshot,
        raw_episodes=raw_episodes[: settings.GRAPHITI_MAX_RAW_EPISODES],
        confirmed_episodes=confirmed_episodes[: settings.GRAPHITI_MAX_CONFIRMED_FACTS],
    )
