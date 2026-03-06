from __future__ import annotations

import json
from dataclasses import dataclass

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from apps.db.models import Article, LLMQueryFilterDropped, LLMQueryFilterKept


@dataclass(slots=True)
class DroppedQueryFilterItem:
    id: int
    doi: str
    article_id: int | None
    article_title: str
    decision_scope_hash: str
    decision_scope_text: str
    scope_summary: str
    score: float | None
    reason: str
    model_name: str
    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None
    decided_at: object


def _scope_summary(scope_text: str) -> str:
    raw = str(scope_text or "").strip()
    if not raw:
        return "-"
    try:
        parsed = json.loads(raw)
    except Exception:
        return raw
    if not isinstance(parsed, dict):
        return raw

    kind = str(parsed.get("kind") or "").strip()
    if kind == "custom_prompt":
        prompt = str(parsed.get("prompt") or "").strip()
        return f"领域提示词：{prompt or '-'}"
    if kind == "query_relevance":
        query = str(parsed.get("raw_query") or "").strip()
        return f"query 相关度：{query or '-'}"
    return raw


def list_dropped_query_filter_entries(
    session: Session,
    *,
    offset: int = 0,
    limit: int = 200,
) -> tuple[list[DroppedQueryFilterItem], int]:
    total = session.scalar(select(func.count()).select_from(LLMQueryFilterDropped)) or 0
    stmt = (
        select(LLMQueryFilterDropped)
        .order_by(desc(LLMQueryFilterDropped.decided_at), desc(LLMQueryFilterDropped.id))
        .offset(max(0, int(offset)))
        .limit(max(1, int(limit)))
    )
    rows = session.scalars(stmt).all()
    if not rows:
        return [], int(total)

    dois = [str(row.doi or "").strip().lower() for row in rows if str(row.doi or "").strip()]
    articles = session.scalars(select(Article).where(Article.doi.in_(dois))).all()
    article_map = {str(article.doi or "").strip().lower(): article for article in articles}

    items: list[DroppedQueryFilterItem] = []
    for row in rows:
        doi = str(row.doi or "").strip().lower()
        article = article_map.get(doi)
        items.append(
            DroppedQueryFilterItem(
                id=row.id,
                doi=doi,
                article_id=article.id if article is not None else None,
                article_title=article.title if article is not None else "",
                decision_scope_hash=str(row.decision_scope_hash or ""),
                decision_scope_text=str(row.decision_scope_text or ""),
                scope_summary=_scope_summary(row.decision_scope_text or ""),
                score=row.score,
                reason=str(row.reason or ""),
                model_name=str(row.model_name or ""),
                prompt_tokens=row.prompt_tokens,
                completion_tokens=row.completion_tokens,
                total_tokens=row.total_tokens,
                decided_at=row.decided_at,
            )
        )
    return items, int(total)


def rescue_dropped_query_filter_entry(session: Session, *, entry_id: int) -> LLMQueryFilterKept | None:
    dropped = session.get(LLMQueryFilterDropped, int(entry_id))
    if dropped is None:
        return None

    kept = session.scalar(
        select(LLMQueryFilterKept).where(
            LLMQueryFilterKept.doi == dropped.doi,
            LLMQueryFilterKept.decision_scope_hash == dropped.decision_scope_hash,
        )
    )
    if kept is None:
        kept = LLMQueryFilterKept(
            doi=dropped.doi,
            decision_scope_hash=dropped.decision_scope_hash,
            decision_scope_text=dropped.decision_scope_text,
        )
        session.add(kept)

    kept.score = dropped.score
    kept.reason = f"手动救回：{str(dropped.reason or '').strip() or '原 drop 记录无原因'}"
    kept.model_name = "manual_rescue"
    kept.prompt_tokens = dropped.prompt_tokens
    kept.completion_tokens = dropped.completion_tokens
    kept.total_tokens = dropped.total_tokens
    kept.decided_at = dropped.decided_at

    session.delete(dropped)
    session.flush()
    return kept
