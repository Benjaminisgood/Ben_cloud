from __future__ import annotations

from dataclasses import dataclass, field
from collections.abc import Callable
from collections import Counter
from datetime import date
import calendar
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.core.config import settings
from apps.db.models import Article, LLMQueryFilterDropped
from apps.models.schemas import IngestResponse, ProviderStats
from apps.providers import ProviderQuery, ProviderRecord, get_all_providers, merge_records
from apps.services.article_service import upsert_provider_record
from apps.services.normalizers import normalize_doi
from apps.services.query_filtering import build_query_filter_runtime
from apps.services.query_planner import build_provider_queries, plan_natural_language_query


@dataclass(slots=True)
class _ProviderExecution:
    provider: str
    fetched: int = 0
    merged: int = 0
    errors: list[str] = field(default_factory=list)


def _emit(log_callback: Callable[[str], None] | None, message: str) -> None:
    if log_callback is not None:
        log_callback(message)


def _clip_text(text: str, limit: int = 220) -> str:
    value = str(text or "")
    if len(value) <= limit:
        return value
    return f"{value[:limit]}..."


def _clean_terms(terms: list[str] | None) -> list[str]:
    if not terms:
        return []
    output: list[str] = []
    seen: set[str] = set()
    for term in terms:
        text = str(term).strip().lower()
        if not text or text in seen:
            continue
        seen.add(text)
        output.append(text)
    return output


def _coerce_provider_query(
    provider_key: str,
    query: ProviderQuery | str | None,
    *,
    raw_query: str,
    query_contexts: list[str],
) -> ProviderQuery:
    if isinstance(query, ProviderQuery):
        return query
    return ProviderQuery(
        provider=provider_key,
        raw_query=raw_query,
        compiled_query=str(query or "").strip() or raw_query,
        query_contexts=list(query_contexts),
    )


def _parse_int(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    text = str(value).strip()
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def _parse_partial_date(value: str, *, end_of_range: bool) -> date | None:
    text = (value or "").strip()
    if not text:
        return None
    text = text.replace("/", "-")

    full = re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})", text)
    if full:
        year, month, day = map(int, full.groups())
        try:
            return date(year, month, day)
        except ValueError:
            return None

    ym = re.fullmatch(r"(\d{4})-(\d{1,2})", text)
    if ym:
        year, month = map(int, ym.groups())
        if month < 1 or month > 12:
            return None
        if end_of_range:
            day = calendar.monthrange(year, month)[1]
            return date(year, month, day)
        return date(year, month, 1)

    y = re.fullmatch(r"(\d{4})", text)
    if y:
        year = int(y.group(1))
        return date(year, 12, 31) if end_of_range else date(year, 1, 1)

    return None


def _record_date_range(value: str) -> tuple[date, date] | None:
    start = _parse_partial_date(value, end_of_range=False)
    end = _parse_partial_date(value, end_of_range=True)
    if start is None or end is None:
        return None
    return start, end


def _build_text_blob(record: ProviderRecord) -> str:
    return " ".join(
        [
            record.title or "",
            record.abstract or "",
            " ".join(record.keywords or []),
            record.journal or "",
            record.publisher or "",
            record.corresponding_author or "",
            " ".join(record.affiliations or []),
        ]
    ).lower()


def _match_record_constraints(
    record: ProviderRecord,
    *,
    published_from: date | None,
    published_to: date | None,
    required_keywords: list[str],
    optional_keywords: list[str],
    excluded_keywords: list[str],
    journal_whitelist: list[str],
    journal_blacklist: list[str],
    min_citation_count: int | None,
    min_impact_factor: float | None,
) -> tuple[bool, str]:
    if published_from is not None or published_to is not None:
        range_value = _record_date_range(record.published_date)
        if range_value is None:
            return False, "date_missing_or_invalid"
        record_start, record_end = range_value
        if published_from is not None and record_end < published_from:
            return False, "date_before_from"
        if published_to is not None and record_start > published_to:
            return False, "date_after_to"

    journal_text = (record.journal or "").strip().lower()
    if journal_whitelist and not any(term in journal_text for term in journal_whitelist):
        return False, "journal_not_in_whitelist"
    if journal_blacklist and any(term in journal_text for term in journal_blacklist):
        return False, "journal_in_blacklist"

    text_blob = _build_text_blob(record)
    if required_keywords and not all(term in text_blob for term in required_keywords):
        return False, "required_keywords_not_met"
    if optional_keywords and not any(term in text_blob for term in optional_keywords):
        return False, "optional_keywords_not_met"
    if excluded_keywords and any(term in text_blob for term in excluded_keywords):
        return False, "excluded_keywords_hit"

    if min_citation_count is not None:
        record_citations = _parse_int(record.citation_count) or 0
        if record_citations < min_citation_count:
            return False, "citation_below_min"

    if min_impact_factor is not None:
        impact = record.impact_factor
        if impact is None:
            return False, "impact_factor_missing"
        if impact < min_impact_factor:
            return False, "impact_factor_below_min"

    return True, "matched"


def _normalized_record_dois(records: list[ProviderRecord]) -> list[str]:
    dois = [str(record.doi or "").strip().lower() for record in records if str(record.doi or "").strip()]
    return [doi for doi in {item for item in dois if item}]


def _load_existing_article_dois(session: Session, records: list[ProviderRecord]) -> set[str]:
    normalized = _normalized_record_dois(records)
    if not normalized:
        return set()
    rows = session.scalars(select(Article.doi).where(Article.doi.in_(normalized))).all()
    return {str(doi or "").strip().lower() for doi in rows if str(doi or "").strip()}


def _load_historical_dropped_decisions(session: Session, records: list[ProviderRecord]) -> dict[str, LLMQueryFilterDropped]:
    normalized = _normalized_record_dois(records)
    if not normalized:
        return {}
    rows = session.scalars(
        select(LLMQueryFilterDropped)
        .where(LLMQueryFilterDropped.doi.in_(normalized))
        .order_by(LLMQueryFilterDropped.decided_at.desc(), LLMQueryFilterDropped.id.desc())
    ).all()
    mapping: dict[str, LLMQueryFilterDropped] = {}
    for row in rows:
        doi = str(row.doi or "").strip().lower()
        if not doi or doi in mapping:
            continue
        mapping[doi] = row
    return mapping


def _should_stop_processing(
    *,
    cancel_check: Callable[[], bool] | None,
    pause_wait_callback: Callable[[], bool] | None,
    log_callback: Callable[[str], None] | None,
) -> bool:
    if pause_wait_callback is not None:
        try:
            cancelled_during_pause = bool(pause_wait_callback())
        except Exception as exc:  # pragma: no cover - 容错日志
            _emit(log_callback, f"任务控制检测失败(pause): {exc}")
            cancelled_during_pause = False
        if cancelled_during_pause:
            _emit(log_callback, "检测到取消请求，任务将在当前安全点停止。")
            return True
    if cancel_check is None:
        return False
    try:
        if cancel_check():
            _emit(log_callback, "检测到取消请求，任务将在当前安全点停止。")
            return True
    except Exception as exc:  # pragma: no cover - 容错日志
        _emit(log_callback, f"任务控制检测失败(cancel): {exc}")
    return False


def ingest_metadata(
    session: Session,
    *,
    query: str | None,
    providers: list[str] | None,
    max_results: int,
    save_tags: list[str] | None,
    query_contexts: list[str] | None = None,
    query_planning_domain_objective: str | None = None,
    query_filter_mode: str | None = None,
    query_similarity_threshold: float | None = None,
    llm_scoring_prompt: str | None = None,
    llm_review_existing_articles: bool = False,
    llm_review_dropped_articles: bool = False,
    published_from: str | None = None,
    published_to: str | None = None,
    required_keywords: list[str] | None = None,
    optional_keywords: list[str] | None = None,
    excluded_keywords: list[str] | None = None,
    journal_whitelist: list[str] | None = None,
    journal_blacklist: list[str] | None = None,
    min_citation_count: int | None = None,
    min_impact_factor: float | None = None,
    cancel_check: Callable[[], bool] | None = None,
    pause_wait_callback: Callable[[], bool] | None = None,
    provider_keys_provider: Callable[[], list[str]] | None = None,
    log_callback: Callable[[str], None] | None = None,
) -> IngestResponse:
    raw_query = (query or "").strip()
    resolved_query = raw_query or settings.default_query
    provider_map = get_all_providers()
    query_contexts = [str(item or "").strip() for item in (query_contexts or []) if str(item or "").strip()]

    provider_keys = _clean_terms(providers or settings.default_providers)
    required_keywords = _clean_terms(required_keywords)
    optional_keywords = _clean_terms(optional_keywords)
    excluded_keywords = _clean_terms(excluded_keywords)
    journal_whitelist = _clean_terms(journal_whitelist)
    journal_blacklist = _clean_terms(journal_blacklist)

    published_from_date = _parse_partial_date(published_from or "", end_of_range=False)
    published_to_date = _parse_partial_date(published_to or "", end_of_range=True)
    if published_from and published_from_date is None:
        _emit(log_callback, f"发布时间下限格式无效: '{published_from}'，已忽略。")
    if published_to and published_to_date is None:
        _emit(log_callback, f"发布时间上限格式无效: '{published_to}'，已忽略。")

    provider_queries: dict[str, ProviderQuery | str] = {key: resolved_query for key in provider_keys}
    plan = plan_natural_language_query(
        resolved_query,
        logger=log_callback,
        domain_objective=query_planning_domain_objective or "",
    )
    provider_queries = build_provider_queries(plan, provider_keys, context_texts=query_contexts)
    if not provider_queries:
        provider_queries = {key: resolved_query for key in provider_keys}
    query_filter_runtime = build_query_filter_runtime(
        mode=query_filter_mode,
        threshold=query_similarity_threshold,
        raw_query=resolved_query,
        plan=plan,
        llm_scoring_prompt=llm_scoring_prompt,
        llm_use_cached_keep=not llm_review_existing_articles,
        llm_use_cached_drop=not llm_review_dropped_articles,
        logger=log_callback,
    )
    _emit(
        log_callback,
        "查询规划完成: "
        f"must={plan.must_terms}, should={plan.should_terms}, exclude={plan.exclude_terms}, "
        f"phrases={plan.phrases}, ai={plan.used_ai}, passthrough={bool(plan.passthrough_query)}",
    )

    _emit(
        log_callback,
        f"开始执行拉取: query='{resolved_query}', providers={provider_keys}, max_results={max_results}",
    )

    aggregated: dict[str, ProviderRecord] = {}
    stats_by_provider: dict[str, _ProviderExecution] = {}
    stats_order: list[str] = []
    cancelled = False

    def _resolve_runtime_provider_keys() -> list[str]:
        if provider_keys_provider is None:
            return list(provider_keys)
        try:
            resolved = _clean_terms(provider_keys_provider())
        except Exception as exc:  # pragma: no cover - 容错日志
            _emit(log_callback, f"读取实时 provider 列表失败，回退到初始列表: {exc}")
            return list(provider_keys)
        if not resolved:
            return list(provider_keys)
        return resolved

    def _trace_for(provider_key: str) -> _ProviderExecution:
        trace = stats_by_provider.get(provider_key)
        if trace is None:
            trace = _ProviderExecution(provider=provider_key)
            stats_by_provider[provider_key] = trace
            stats_order.append(provider_key)
        return trace

    pending_provider_keys = list(provider_keys)
    processed_provider_keys: set[str] = set()
    while True:
        if _should_stop_processing(
            cancel_check=cancel_check,
            pause_wait_callback=pause_wait_callback,
            log_callback=log_callback,
        ):
            cancelled = True
            break

        runtime_provider_keys = _resolve_runtime_provider_keys()
        runtime_provider_set = set(runtime_provider_keys)
        for runtime_provider_key in runtime_provider_keys:
            if runtime_provider_key in processed_provider_keys or runtime_provider_key in pending_provider_keys:
                continue
            pending_provider_keys.append(runtime_provider_key)
            _emit(log_callback, f"[runtime] 检测到新增 provider={runtime_provider_key}，已加入执行队列。")

        if not pending_provider_keys:
            break

        provider_key = pending_provider_keys.pop(0)
        trace = _trace_for(provider_key)

        if provider_key not in runtime_provider_set:
            trace.errors.append("provider_disabled_runtime")
            _emit(log_callback, f"[{provider_key}] provider_disabled_runtime，已跳过。")
            continue

        processed_provider_keys.add(provider_key)

        provider = provider_map.get(provider_key)
        if provider is None:
            trace.errors.append("provider_not_found")
            _emit(log_callback, f"[{provider_key}] provider_not_found，已跳过。")
            continue
        if not provider.is_configured():
            trace.errors.append("provider_not_configured")
            _emit(log_callback, f"[{provider_key}] provider_not_configured，已跳过。")
            continue

        if provider_key not in provider_queries:
            runtime_provider_query: ProviderQuery | str | None = None
            try:
                runtime_queries = build_provider_queries(plan, [provider_key], context_texts=query_contexts)
                if isinstance(runtime_queries, dict):
                    runtime_provider_query = runtime_queries.get(provider_key)
            except Exception as exc:  # pragma: no cover - 容错日志
                _emit(log_callback, f"[{provider_key}] 动态生成 query 失败，回退到原始 query: {exc}")
            if runtime_provider_query is None:
                provider_queries[provider_key] = resolved_query
                _emit(log_callback, f"[{provider_key}] 动态新增 provider 未命中查询规划，回退到原始 query。")
            else:
                provider_queries[provider_key] = runtime_provider_query

        provider_query = _coerce_provider_query(
            provider_key,
            provider_queries.get(provider_key, resolved_query),
            raw_query=resolved_query,
            query_contexts=query_contexts,
        )
        scope_note = ""
        if provider_query.domain_scope_name:
            scope_terms = ",".join(provider_query.domain_scope_terms[:6])
            scope_note = (
                f", domain_scope={provider_query.domain_scope_name}"
                f", scope_terms={scope_terms}"
            )
        _emit(
            log_callback,
            f"[{provider_key}] 开始抓取... field={provider_query.query_field}, "
            f"query={_clip_text(provider_query.compiled_query)}{scope_note}",
        )
        try:
            records = provider.search(provider_query, max_results=max_results)
            trace.fetched = len(records)
            _emit(log_callback, f"[{provider_key}] 抓取完成: fetched={trace.fetched}")
        except Exception as exc:  # pragma: no cover - 网络层容错
            trace.errors.append(str(exc))
            _emit(log_callback, f"[{provider_key}] 抓取失败: {exc}")
            continue

        for raw_record in records:
            if _should_stop_processing(
                cancel_check=cancel_check,
                pause_wait_callback=pause_wait_callback,
                log_callback=log_callback,
            ):
                cancelled = True
                break
            doi = normalize_doi(raw_record.doi)
            if not doi:
                continue
            raw_record.doi = doi

            current = aggregated.get(doi)
            if current is None:
                aggregated[doi] = raw_record
                trace.merged += 1
            else:
                aggregated[doi] = merge_records(current, raw_record)

        if cancelled:
            _emit(log_callback, f"[{provider_key}] 检测到取消请求，结束当前 provider 合并阶段。")
            break

        _emit(log_callback, f"[{provider_key}] 去重合并后新增 unique={trace.merged}")

    total_aggregated = len(aggregated)
    _emit(log_callback, f"跨源聚合完成: unique_doi={total_aggregated}。")

    prefiltered_records: list[ProviderRecord] = []
    dropped_reasons: Counter[str] = Counter()
    for record in aggregated.values():
        if _should_stop_processing(
            cancel_check=cancel_check,
            pause_wait_callback=pause_wait_callback,
            log_callback=log_callback,
        ):
            cancelled = True
            break
        ok, reason = _match_record_constraints(
            record,
            published_from=published_from_date,
            published_to=published_to_date,
            required_keywords=required_keywords,
            optional_keywords=optional_keywords,
            excluded_keywords=excluded_keywords,
            journal_whitelist=journal_whitelist,
            journal_blacklist=journal_blacklist,
            min_citation_count=min_citation_count,
            min_impact_factor=min_impact_factor,
        )
        if ok:
            prefiltered_records.append(record)
        else:
            dropped_reasons[reason] += 1

    existing_article_dois: set[str] = set()
    historical_dropped: dict[str, LLMQueryFilterDropped] = {}
    if query_filter_runtime.effective_mode == "llm" and prefiltered_records:
        if not llm_review_existing_articles:
            existing_article_dois = _load_existing_article_dois(session, prefiltered_records)
            if existing_article_dois:
                _emit(
                    log_callback,
                    f"query 结果复核[llm]: 已启用“已入库不二次复核”，命中 existing_doi={len(existing_article_dois)}。",
                )
        if not llm_review_dropped_articles:
            historical_dropped = _load_historical_dropped_decisions(session, prefiltered_records)
            if historical_dropped:
                _emit(
                    log_callback,
                    f"query 结果复核[llm]: 已启用“历史 drop 直接跳过复核”，命中 dropped_doi={len(historical_dropped)}。",
                )

    if not cancelled:
        query_filter_runtime.prepare(session, prefiltered_records, logger=log_callback)

    inserted = 0
    updated = 0
    skipped = 0
    kept_records: list[ProviderRecord] = []
    needs_embedding_persist = query_filter_runtime.effective_mode == "embedding"
    kept_count = 0

    _emit(log_callback, "开始逐篇复核并写入 SQLite...")
    total_candidates = len(prefiltered_records)
    for idx, record in enumerate(prefiltered_records, start=1):
        if _should_stop_processing(
            cancel_check=cancel_check,
            pause_wait_callback=pause_wait_callback,
            log_callback=log_callback,
        ):
            cancelled = True
            break
        _emit(log_callback, f"逐篇处理开始: {idx}/{total_candidates} doi={record.doi or '-'}")
        doi_key = str(record.doi or "").strip().lower()
        if query_filter_runtime.effective_mode == "llm" and doi_key in existing_article_dois:
            ok, reason = True, "matched"
            _emit(
                log_callback,
                "query 结果复核[llm]: "
                f"doi={record.doi or '-'} action=keep source=existing_article_no_rereview",
            )
        elif query_filter_runtime.effective_mode == "llm" and doi_key in historical_dropped:
            cached = historical_dropped[doi_key]
            ok, reason = False, "query_llm_historical_drop"
            _emit(
                log_callback,
                "query 结果复核[llm]: "
                f"doi={record.doi or '-'} action=drop source=historical_drop_cache "
                f"last_model={str(cached.model_name or '-').strip()} last_score={float(cached.score or 0.0):.4f}",
            )
        else:
            ok, reason = query_filter_runtime.match(record, session=session, logger=log_callback)
        if not ok:
            dropped_reasons[reason] += 1
            if query_filter_runtime.effective_mode == "llm":
                session.commit()
                session.expunge_all()
            _emit(
                log_callback,
                f"逐篇处理: {idx}/{total_candidates} doi={record.doi or '-'} action=drop reason={reason}",
            )
            continue

        status = upsert_provider_record(session, record, save_tags=save_tags)
        kept_count += 1
        if needs_embedding_persist:
            kept_records.append(record)
        if status == "inserted":
            inserted += 1
        elif status == "updated":
            updated += 1
        else:
            skipped += 1

        session.commit()
        session.expunge_all()
        _emit(
            log_callback,
            "逐篇入库完成: "
            f"{idx}/{total_candidates} doi={record.doi or '-'} status={status} "
            f"(inserted={inserted}, updated={updated}, skipped={skipped})",
        )

    if cancelled:
        _emit(log_callback, "任务已按取消/暂停控制提前结束，返回当前已处理结果。")

    query_filter_runtime.persist(session, kept_records, logger=log_callback)
    session.commit()
    query_filter_runtime.emit_summary(logger=log_callback)

    _emit(
        log_callback,
        f"约束过滤完成: kept={kept_count}, dropped={total_aggregated - kept_count}",
    )
    if dropped_reasons:
        _emit(
            log_callback,
            "过滤原因统计: "
            + ", ".join(f"{reason}={count}" for reason, count in dropped_reasons.items()),
        )
    _emit(
        log_callback,
        f"执行完成: inserted={inserted}, updated={updated}, skipped={skipped}, merged_unique={len(aggregated)}",
    )

    provider_stats = []
    for provider_key in stats_order:
        item = stats_by_provider[provider_key]
        provider_stats.append(
            ProviderStats(provider=item.provider, fetched=item.fetched, merged=item.merged, errors=item.errors)
        )

    return IngestResponse(
        query=resolved_query,
        inserted=inserted,
        updated=updated,
        skipped=skipped,
        merged_unique=total_aggregated,
        provider_stats=provider_stats,
    )
