from __future__ import annotations

import hashlib
import json
import math
import statistics
import struct
from collections import Counter
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.core.config import settings
from apps.core.http_clients import build_openai_client
from apps.db.models import Article, LLMQueryFilterDropped, LLMQueryFilterKept
from apps.providers import ProviderRecord
from apps.services.normalizers import normalize_list, split_semicolon
from apps.services.query_planner import (
    QueryBooleanFilter,
    QueryPlan,
    build_query_boolean_filter,
    build_query_embedding_text,
)

try:
    from openai import OpenAI
except Exception:  # pragma: no cover
    OpenAI = None  # type: ignore[assignment]

FilterLog = Callable[[str], None] | None
SUPPORTED_QUERY_FILTER_MODES = {"none", "embedding", "boolean", "llm"}
DEFAULT_QUERY_FILTER_MODE = "embedding"
DEFAULT_EMBEDDING_THRESHOLD = 0.35
_EMBEDDING_BATCH_SIZE = 32


def _emit(logger: FilterLog, message: str) -> None:
    if logger is not None:
        logger(message)


def _parse_json_object(raw: str) -> dict[str, object]:
    text = str(raw or "").strip()
    if not text:
        return {}
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


def _normalize_score(value: object) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        score = 0.0
    return min(max(score, 0.0), 1.0)


def _normalize_free_text(value: object) -> str:
    return " ".join(str(value or "").split()).strip()


def _normalize_token_count(value: object) -> int:
    try:
        count = int(value)
    except (TypeError, ValueError):
        count = 0
    return max(0, count)


def _normalize_match_terms(items: Iterable[object]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for item in items:
        text = " ".join(str(item or "").strip().lower().split())
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def _missing_terms(text: str, terms: Iterable[str]) -> list[str]:
    haystack = str(text or "").lower()
    return [term for term in _normalize_match_terms(terms) if term not in haystack]


def _create_openai_client() -> OpenAI | None:
    api_key = (settings.aliyun_ai_api_key or "").strip().strip("'\"")
    base_url = (settings.aliyun_ai_api_base_url or "").strip().strip("'\"")
    if not api_key or OpenAI is None:
        return None
    return build_openai_client(
        api_key=api_key,
        base_url=base_url,
        timeout=max(1.0, float(settings.request_timeout_seconds)),
    )


def _chat_model_name(value: str | None = None) -> str:
    return _normalize_free_text(value or settings.aliyun_ai_model or "qwen-plus") or "qwen-plus"


def _resolve_llm_scoring_prompt(value: str | None) -> str:
    return _normalize_free_text(value)


def _llm_model_candidates() -> list[str]:
    return normalize_list([_chat_model_name()] + list(settings.query_filter_llm_fallback_models or []))


def _normalize_embedding_dimensions(value: object) -> int:
    try:
        dims = int(value)
    except (TypeError, ValueError):
        dims = 1024
    return max(1, dims)


def _embedding_model_name() -> str:
    return (settings.aliyun_ai_embedding_model or "text-embedding-v4").strip().strip("'\"") or "text-embedding-v4"


def _record_text(record: ProviderRecord, *, limit: int = 8000) -> str:
    parts = []
    if record.title:
        parts.append(f"Title: {record.title}")
    if record.abstract:
        parts.append(f"Abstract: {record.abstract}")
    if record.keywords:
        parts.append(f"Keywords: {', '.join(record.keywords)}")
    if record.journal:
        parts.append(f"Journal: {record.journal}")
    if record.publisher:
        parts.append(f"Publisher: {record.publisher}")
    if record.corresponding_author:
        parts.append(f"Corresponding author: {record.corresponding_author}")
    if record.affiliations:
        parts.append(f"Affiliations: {', '.join(record.affiliations)}")
    if record.source:
        parts.append(f"Source: {record.source}")
    if record.published_date:
        parts.append(f"Published date: {record.published_date}")
    text = "\n".join(parts).strip()
    if len(text) <= limit:
        return text
    return text[:limit]


def _merged_record_text(article: Article | None, record: ProviderRecord, *, limit: int = 8000) -> str:
    title = record.title or (article.title if article is not None else "")

    existing_abstract = article.abstract if article is not None else ""
    abstract = existing_abstract
    if record.abstract and len(record.abstract) >= len(existing_abstract or ""):
        abstract = record.abstract

    journal = record.journal or (article.journal if article is not None else "")
    publisher = record.publisher or (article.publisher if article is not None else "")
    corresponding_author = record.corresponding_author or (
        article.corresponding_author if article is not None else ""
    )
    source = record.source or (article.source if article is not None else "")
    published_date = record.published_date or (article.published_date if article is not None else "")

    existing_keywords = split_semicolon(article.keywords) if article is not None else []
    merged_keywords = normalize_list(existing_keywords + (record.keywords or []))

    existing_affiliations = split_semicolon(article.affiliations) if article is not None else []
    merged_affiliations = normalize_list(existing_affiliations + (record.affiliations or []))

    merged = ProviderRecord(
        doi=record.doi or (article.doi if article is not None else ""),
        title=title,
        abstract=abstract,
        keywords=merged_keywords,
        journal=journal,
        publisher=publisher,
        corresponding_author=corresponding_author,
        affiliations=merged_affiliations,
        source=source,
        published_date=published_date,
    )
    return _record_text(merged, limit=limit)


def _hash_text(text: str) -> str:
    return hashlib.sha256(str(text or "").encode("utf-8")).hexdigest()


def _pack_embedding(values: list[float]) -> bytes:
    if not values:
        return b""
    return struct.pack(f"<{len(values)}f", *values)


def _unpack_embedding(blob: bytes | None, dimensions: int | None) -> list[float] | None:
    if not blob:
        return None
    dims = int(dimensions or 0)
    if dims <= 0:
        return None
    expected = dims * 4
    if len(blob) != expected:
        return None
    return list(struct.unpack(f"<{dims}f", blob))


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return dot / (left_norm * right_norm)


def _embedding_vectors(
    client: OpenAI,
    *,
    texts: list[str],
    model_name: str,
    dimensions: int,
) -> list[list[float]]:
    if not texts:
        return []
    response = client.embeddings.create(
        model=model_name,
        input=texts,
        dimensions=dimensions,
    )
    ordered = sorted(response.data, key=lambda item: item.index)
    return [list(item.embedding) for item in ordered]


@dataclass(slots=True)
class LLMTokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass(slots=True)
class LLMDecisionCacheEntry:
    doi: str
    kept: bool
    score: float
    reason: str
    model_name: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    decided_at: datetime | None


def _llm_decision_scope(
    *,
    raw_query: str,
    plan: QueryPlan,
    boolean_filter: QueryBooleanFilter | None,
    llm_scoring_prompt: str,
) -> tuple[str, str]:
    scope_text = json.dumps(
        {
            "kind": "query_relevance",
            "raw_query": raw_query,
            "must_terms": plan.must_terms,
            "should_terms": plan.should_terms,
            "exclude_terms": plan.exclude_terms,
            "phrases": plan.phrases,
            "domain_objective": plan.domain_objective,
            "boolean_filter": boolean_filter.describe() if boolean_filter is not None else "",
            "review_constraints": llm_scoring_prompt,
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    return _hash_text(scope_text), scope_text


def _extract_chat_usage(response: object) -> LLMTokenUsage:
    usage = getattr(response, "usage", None)
    if usage is None:
        return LLMTokenUsage()
    return LLMTokenUsage(
        prompt_tokens=_normalize_token_count(getattr(usage, "prompt_tokens", 0)),
        completion_tokens=_normalize_token_count(getattr(usage, "completion_tokens", 0)),
        total_tokens=_normalize_token_count(getattr(usage, "total_tokens", 0)),
    )


def _build_llm_scoring_payload(
    *,
    record: ProviderRecord,
    plan: QueryPlan,
    raw_query: str,
    boolean_filter: QueryBooleanFilter | None,
    llm_scoring_prompt: str | None,
) -> dict[str, object]:
    article = {
        "doi": record.doi,
        "title": record.title,
        "abstract": record.abstract,
        "keywords": record.keywords,
        "journal": record.journal,
        "publisher": record.publisher,
        "corresponding_author": record.corresponding_author,
        "affiliations": record.affiliations,
        "source": record.source,
        "published_date": record.published_date,
    }
    payload: dict[str, object] = {
        "task": "Score how relevant this candidate paper is to the current search request.",
        "query": {
            "raw": raw_query,
            "must_terms": plan.must_terms,
            "should_terms": plan.should_terms,
            "exclude_terms": plan.exclude_terms,
            "phrases": plan.phrases,
            "domain_objective": plan.domain_objective,
            "boolean_filter": boolean_filter.describe() if boolean_filter is not None else "",
        },
        "article": article,
        "rules": [
            "Return JSON only. Do not add explanations.",
            "score must be a float between 0 and 1, where 1 means highly relevant and 0 means essentially irrelevant.",
            "Treat the raw query and the extracted must_terms, should_terms, exclude_terms, phrases, boolean_filter, and domain_objective together as the relevance target.",
            "The main query or tag remains primary. The domain objective only narrows the context and must not replace the main target.",
            "If must_terms are missing or exclude_terms are clearly violated, the score should drop significantly.",
            "Allow semantic matches, terminology variants, abbreviations, and expanded forms. Do not require literal word-for-word overlap.",
            "Keep reason short and in English.",
        ],
        "output_schema": {
            "score": 0.0,
            "reason": "One short reason.",
        },
    }
    review_constraints = _normalize_free_text(llm_scoring_prompt)
    if review_constraints:
        payload["review_constraints"] = review_constraints
        rules = payload.get("rules")
        if isinstance(rules, list):
            rules.append(
                "review_constraints are additional constraints for this review pass only; follow them strictly."
            )
    return payload


def _score_record_with_llm(
    client: OpenAI,
    *,
    record: ProviderRecord,
    plan: QueryPlan,
    raw_query: str,
    boolean_filter: QueryBooleanFilter | None,
    llm_scoring_prompt: str | None,
    model_name: str,
) -> tuple[float, str, LLMTokenUsage, str]:
    payload = _build_llm_scoring_payload(
        record=record,
        plan=plan,
        raw_query=raw_query,
        boolean_filter=boolean_filter,
        llm_scoring_prompt=llm_scoring_prompt,
    )

    response = client.chat.completions.create(
        model=model_name,
        temperature=0,
        messages=[
            {"role": "system", "content": "You are a rigorous research-paper relevance evaluator for chemistry and catalysis literature."},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ],
        response_format={"type": "json_object"},
    )
    content = ""
    if response.choices:
        content = str((response.choices[0].message.content or "")).strip()

    parsed = _parse_json_object(content)
    score = _normalize_score(parsed.get("score"))
    reason = str(parsed.get("reason") or "").strip()
    usage = _extract_chat_usage(response)
    actual_model = _normalize_free_text(getattr(response, "model", "")) or model_name
    return score, reason, usage, actual_model


@dataclass(slots=True)
class QueryFilterRuntime:
    requested_mode: str
    effective_mode: str
    threshold: float
    raw_query: str
    plan: QueryPlan
    boolean_filter: QueryBooleanFilter | None
    llm_scoring_prompt: str = ""
    llm_decision_scope_hash: str = ""
    llm_decision_scope_text: str = ""
    llm_use_cached_keep: bool = True
    llm_use_cached_drop: bool = True
    client: OpenAI | None = None
    embedding_model: str = field(default_factory=_embedding_model_name)
    embedding_dimensions: int = field(default_factory=lambda: _normalize_embedding_dimensions(settings.aliyun_ai_embedding_dimensions))
    embedding_query_text: str = ""
    query_embedding: list[float] | None = None
    embedding_scores: dict[str, float] = field(default_factory=dict)
    record_embeddings: dict[str, list[float]] = field(default_factory=dict)
    record_text_hashes: dict[str, str] = field(default_factory=dict)
    embedding_score_sources: dict[str, str] = field(default_factory=dict)
    embedding_precheck_failures: dict[str, list[str]] = field(default_factory=dict)
    llm_scores: dict[str, float] = field(default_factory=dict)
    llm_reasons: dict[str, str] = field(default_factory=dict)
    llm_models: dict[str, str] = field(default_factory=dict)
    llm_token_usages: dict[str, LLMTokenUsage] = field(default_factory=dict)
    llm_cached_kept: dict[str, LLMDecisionCacheEntry] = field(default_factory=dict)
    llm_cached_dropped: dict[str, LLMDecisionCacheEntry] = field(default_factory=dict)
    llm_model_candidates: list[str] = field(default_factory=_llm_model_candidates)
    llm_active_model: str = ""
    llm_prompt_tokens_total: int = 0
    llm_completion_tokens_total: int = 0
    llm_total_tokens_total: int = 0
    llm_api_calls: int = 0
    llm_cache_hits_kept: int = 0
    llm_cache_hits_dropped: int = 0

    def describe(self) -> str:
        parts = [f"requested={self.requested_mode}", f"effective={self.effective_mode}"]
        if self.effective_mode == "embedding":
            parts.append(f"threshold={self.threshold:.2f}")
            parts.append(f"model={self.embedding_model}")
            parts.append(f"dims={self.embedding_dimensions}")
            must_terms = _normalize_match_terms(self.plan.must_terms)
            if must_terms:
                parts.append(f"must_terms_precheck={must_terms}")
        if self.effective_mode == "boolean" and self.boolean_filter is not None:
            parts.append(f"expr={self.boolean_filter.describe()}")
        if self.effective_mode == "llm":
            parts.append("scope=per-record-score")
            parts.append(f"threshold={self.threshold:.2f}")
            parts.append("strategy=query_relevance")
            if self.llm_model_candidates:
                parts.append(f"models={self.llm_model_candidates}")
            if self.llm_decision_scope_hash:
                parts.append(f"decision_scope={self.llm_decision_scope_hash[:12]}")
            parts.append(f"keep_cache={'on' if self.llm_use_cached_keep else 'off'}")
            parts.append(f"drop_cache={'on' if self.llm_use_cached_drop else 'off'}")
        return ", ".join(parts)

    def close(self) -> None:
        if self.client is None:
            return
        try:
            self.client.close()
        except Exception:
            pass

    def prepare(self, session: Session, records: Iterable[ProviderRecord], *, logger: FilterLog = None) -> None:
        items = list(records)
        if self.effective_mode == "llm":
            self._prepare_llm_cache(session, items, logger=logger)
            return
        if self.effective_mode != "embedding":
            return
        if not items:
            _emit(logger, "query 结果复核: embedding 模式无候选记录，跳过。")
            return
        if self.client is None:
            self._fallback(logger, "embedding 客户端不可用")
            return
        if not self.embedding_query_text:
            self._fallback(logger, "embedding query 文本为空")
            return

        try:
            self.query_embedding = _embedding_vectors(
                self.client,
                texts=[self.embedding_query_text],
                model_name=self.embedding_model,
                dimensions=self.embedding_dimensions,
            )[0]
        except Exception as exc:  # pragma: no cover - 网络容错
            self._fallback(logger, f"query embedding 生成失败: {exc}")
            return

        if self.effective_mode != "embedding" or self.query_embedding is None:
            return

        cached_rows = self._load_cached_articles(session, [record.doi for record in items])
        to_embed: list[tuple[ProviderRecord, str]] = []
        reused = 0
        precheck_dropped = 0
        must_terms = _normalize_match_terms(self.plan.must_terms)

        for record in items:
            doi = str(record.doi or "").strip().lower()
            cached = cached_rows.get(doi)
            text = _merged_record_text(cached, record)
            text_hash = _hash_text(text)
            self.record_text_hashes[doi] = text_hash
            if not text:
                self.embedding_scores[doi] = 0.0
                self.embedding_score_sources[doi] = "empty"
                continue
            missing = _missing_terms(text, must_terms)
            if missing:
                self.embedding_scores[doi] = 0.0
                self.embedding_score_sources[doi] = "must_terms"
                self.embedding_precheck_failures[doi] = missing
                precheck_dropped += 1
                continue

            vector = self._reuse_cached_vector(cached, text_hash)
            if vector is not None:
                self.record_embeddings[doi] = vector
                self.embedding_scores[doi] = _cosine_similarity(self.query_embedding, vector)
                self.embedding_score_sources[doi] = "cache"
                reused += 1
                continue

            to_embed.append((record, text))

        computed = 0
        for idx in range(0, len(to_embed), _EMBEDDING_BATCH_SIZE):
            batch = to_embed[idx : idx + _EMBEDDING_BATCH_SIZE]
            batch_texts = [text for _, text in batch]
            try:
                vectors = _embedding_vectors(
                    self.client,
                    texts=batch_texts,
                    model_name=self.embedding_model,
                    dimensions=self.embedding_dimensions,
                )
            except Exception as exc:  # pragma: no cover - 网络容错
                self._fallback(logger, f"候选文献 embedding 生成失败: {exc}")
                return

            for (record, text), vector in zip(batch, vectors):
                doi = str(record.doi or "").strip().lower()
                self.record_embeddings[doi] = vector
                self.record_text_hashes[doi] = _hash_text(text)
                self.embedding_scores[doi] = _cosine_similarity(self.query_embedding, vector)
                self.embedding_score_sources[doi] = "api"
                computed += 1

        if self.embedding_scores:
            scores = list(self.embedding_scores.values())
            _emit(
                logger,
                "query 结果复核: embedding 逐篇打分完成 "
                f"(count={len(scores)}, must_precheck_dropped={precheck_dropped}, reused={reused}, embedded={computed}, threshold={self.threshold:.2f}, "
                f"min={min(scores):.3f}, avg={statistics.mean(scores):.3f}, max={max(scores):.3f})",
            )

    def match(
        self,
        record: ProviderRecord,
        *,
        session: Session | None = None,
        logger: FilterLog = None,
    ) -> tuple[bool, str]:
        if self.effective_mode == "none":
            return True, "matched"
        if self.effective_mode == "boolean":
            if self.boolean_filter is None:
                return True, "matched"
            matched = self.boolean_filter.matches(_record_text(record, limit=12000).lower())
            return (True, "matched") if matched else (False, "query_boolean_filter_not_matched")
        if self.effective_mode == "embedding":
            doi = str(record.doi or "").strip().lower()
            score = float(self.embedding_scores.get(doi, 0.0))
            source = self.embedding_score_sources.get(doi, "unknown")
            if source == "must_terms":
                missing = ", ".join(self.embedding_precheck_failures.get(doi, [])) or "-"
                _emit(
                    logger,
                    "query 结果复核[embedding]: "
                    f"doi={record.doi or '-'} score={score:.4f} threshold={self.threshold:.4f} "
                    f"source={source} action=drop missing={missing}",
                )
                return False, "query_embedding_must_terms_not_matched"
            matched = score >= self.threshold
            _emit(
                logger,
                "query 结果复核[embedding]: "
                f"doi={record.doi or '-'} score={score:.4f} threshold={self.threshold:.4f} "
                f"source={source} action={'keep' if matched else 'drop'}",
            )
            return (True, "matched") if matched else (False, "query_embedding_below_threshold")
        if self.effective_mode == "llm":
            return self._match_with_llm(record, session=session, logger=logger)
        return True, "matched"

    def persist(self, session: Session, records: Iterable[ProviderRecord], *, logger: FilterLog = None) -> None:
        if self.effective_mode != "embedding":
            return
        dois = [str(record.doi or "").strip().lower() for record in records if str(record.doi or "").strip()]
        if not dois:
            return

        articles = session.scalars(select(Article).where(Article.doi.in_(dois))).all()
        persisted = 0
        for article in articles:
            doi = str(article.doi or "").strip().lower()
            vector = self.record_embeddings.get(doi)
            text_hash = self.record_text_hashes.get(doi)
            if not vector or not text_hash:
                continue
            article_text_hash = _hash_text(
                _merged_record_text(
                    article,
                    ProviderRecord(
                        doi=article.doi,
                        title=article.title,
                        abstract=article.abstract,
                        keywords=split_semicolon(article.keywords),
                        journal=article.journal,
                        publisher=article.publisher,
                        corresponding_author=article.corresponding_author,
                        affiliations=split_semicolon(article.affiliations),
                        source=article.source,
                        published_date=article.published_date,
                    ),
                )
            )
            if article_text_hash != text_hash:
                _emit(logger, f"query 结果复核: doi={article.doi} 当前文章文本已变化，跳过写入旧 embedding。")
                continue
            payload = _pack_embedding(vector)
            if (
                article.embedding_vector == payload
                and article.embedding_model == self.embedding_model
                and article.embedding_dimensions == self.embedding_dimensions
                and article.embedding_text_hash == text_hash
            ):
                continue
            article.embedding_vector = payload
            article.embedding_model = self.embedding_model
            article.embedding_dimensions = self.embedding_dimensions
            article.embedding_text_hash = text_hash
            article.embedding_updated_at = datetime.utcnow()
            persisted += 1
        if persisted:
            session.flush()
            _emit(logger, f"query 结果复核: 已写入/更新 SQLite embedding 缓存 {persisted} 条。")

    def emit_summary(self, *, logger: FilterLog = None) -> None:
        if self.effective_mode == "embedding":
            if not self.embedding_precheck_failures:
                return
            counts: Counter[str] = Counter()
            for missing_terms in self.embedding_precheck_failures.values():
                counts.update(missing_terms)
            if not counts:
                return
            ordered = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
            rendered = ", ".join(f"{term}={count}" for term, count in ordered)
            _emit(logger, f"query 结果复核[embedding]: must_terms 缺失词统计: {rendered}")
            return
        if self.effective_mode != "llm":
            return
        _emit(
            logger,
            "query 结果复核[llm]: token 统计 "
            f"(api_calls={self.llm_api_calls}, prompt_tokens={self.llm_prompt_tokens_total}, "
            f"completion_tokens={self.llm_completion_tokens_total}, total_tokens={self.llm_total_tokens_total}, "
            f"cached_keep={self.llm_cache_hits_kept}, cached_drop={self.llm_cache_hits_dropped})",
        )

    def _load_cached_articles(self, session: Session, dois: list[str]) -> dict[str, Article]:
        normalized = [doi for doi in {str(item or "").strip().lower() for item in dois} if doi]
        if not normalized:
            return {}
        rows = session.scalars(select(Article).where(Article.doi.in_(normalized))).all()
        return {str(row.doi or "").strip().lower(): row for row in rows}

    def _reuse_cached_vector(self, article: Article | None, text_hash: str) -> list[float] | None:
        if article is None:
            return None
        if article.embedding_model != self.embedding_model:
            return None
        if int(article.embedding_dimensions or 0) != self.embedding_dimensions:
            return None
        if article.embedding_text_hash != text_hash:
            return None
        return _unpack_embedding(article.embedding_vector, article.embedding_dimensions)

    def _prepare_llm_cache(self, session: Session, records: list[ProviderRecord], *, logger: FilterLog = None) -> None:
        if not self.llm_decision_scope_hash or not records:
            return
        if not self.llm_use_cached_keep and not self.llm_use_cached_drop:
            _emit(logger, "query 结果复核[llm]: 已关闭 keep/drop SQLite 缓存，全部候选将走实时判定。")
            return
        dois = [str(record.doi or "").strip().lower() for record in records if str(record.doi or "").strip()]
        normalized = [doi for doi in {item for item in dois if item}]
        if not normalized:
            return

        _emit(
            logger,
            "query 结果复核[llm]: 开始加载 SQLite 复核缓存 "
            f"(candidates={len(normalized)}, scope={self.llm_decision_scope_hash[:12]})",
        )

        kept_rows: list[LLMQueryFilterKept] = []
        dropped_rows: list[LLMQueryFilterDropped] = []
        if self.llm_use_cached_keep:
            kept_rows = session.scalars(
                select(LLMQueryFilterKept).where(
                    LLMQueryFilterKept.doi.in_(normalized),
                    LLMQueryFilterKept.decision_scope_hash == self.llm_decision_scope_hash,
                )
            ).all()
        if self.llm_use_cached_drop:
            dropped_rows = session.scalars(
                select(LLMQueryFilterDropped).where(
                    LLMQueryFilterDropped.doi.in_(normalized),
                    LLMQueryFilterDropped.decision_scope_hash == self.llm_decision_scope_hash,
                )
            ).all()

        for row in kept_rows:
            doi = str(row.doi or "").strip().lower()
            self.llm_cached_kept[doi] = LLMDecisionCacheEntry(
                doi=doi,
                kept=True,
                score=_normalize_score(row.score),
                reason=str(row.reason or "").strip(),
                model_name=str(row.model_name or "").strip(),
                prompt_tokens=_normalize_token_count(row.prompt_tokens),
                completion_tokens=_normalize_token_count(row.completion_tokens),
                total_tokens=_normalize_token_count(row.total_tokens),
                decided_at=row.decided_at,
            )
        for row in dropped_rows:
            doi = str(row.doi or "").strip().lower()
            self.llm_cached_dropped[doi] = LLMDecisionCacheEntry(
                doi=doi,
                kept=False,
                score=_normalize_score(row.score),
                reason=str(row.reason or "").strip(),
                model_name=str(row.model_name or "").strip(),
                prompt_tokens=_normalize_token_count(row.prompt_tokens),
                completion_tokens=_normalize_token_count(row.completion_tokens),
                total_tokens=_normalize_token_count(row.total_tokens),
                decided_at=row.decided_at,
            )

        overlap = set(self.llm_cached_kept).intersection(self.llm_cached_dropped)
        for doi in overlap:
            self.llm_cached_kept.pop(doi, None)

        _emit(
            logger,
            "query 结果复核[llm]: 已加载 SQLite 复核缓存 "
            f"(keep={len(self.llm_cached_kept)}, drop={len(self.llm_cached_dropped)}, scope={self.llm_decision_scope_hash[:12]})",
        )

    def _score_with_llm_model_fallback(
        self,
        record: ProviderRecord,
        *,
        logger: FilterLog = None,
    ) -> tuple[float, str, LLMTokenUsage, str]:
        candidates = self.llm_model_candidates or [_chat_model_name()]
        if not self.llm_active_model:
            self.llm_active_model = candidates[0]
        if self.llm_active_model in candidates:
            start_index = candidates.index(self.llm_active_model)
        else:
            start_index = 0

        attempted = candidates[start_index:] + candidates[:start_index]
        failures: list[str] = []
        for candidate in attempted:
            _emit(logger, f"query 结果复核[llm]: 开始请求模型 model={candidate}")
            try:
                score, reason, usage, actual_model = _score_record_with_llm(
                    self.client,
                    record=record,
                    plan=self.plan,
                    raw_query=self.raw_query,
                    boolean_filter=self.boolean_filter,
                    llm_scoring_prompt=self.llm_scoring_prompt,
                    model_name=candidate,
                )
                if candidate != self.llm_active_model:
                    _emit(logger, f"query 结果复核[llm]: 自动切换到备用模型 {candidate}")
                self.llm_active_model = candidate
                return score, reason, usage, actual_model
            except Exception as exc:  # pragma: no cover - 网络容错
                failures.append(f"{candidate}: {exc}")
                _emit(logger, f"query 结果复核[llm]: model={candidate} 判定失败，准备尝试下一个模型。error={exc}")
        raise RuntimeError(" | ".join(failures) if failures else "LLM 判定失败")

    def _persist_llm_decision(
        self,
        session: Session,
        *,
        doi: str,
        kept: bool,
        score: float,
        reason: str,
        model_name: str,
        usage: LLMTokenUsage,
    ) -> None:
        if not self.llm_decision_scope_hash:
            return

        keep_row = session.scalar(
            select(LLMQueryFilterKept).where(
                LLMQueryFilterKept.doi == doi,
                LLMQueryFilterKept.decision_scope_hash == self.llm_decision_scope_hash,
            )
        )
        drop_row = session.scalar(
            select(LLMQueryFilterDropped).where(
                LLMQueryFilterDropped.doi == doi,
                LLMQueryFilterDropped.decision_scope_hash == self.llm_decision_scope_hash,
            )
        )

        target_cls = LLMQueryFilterKept if kept else LLMQueryFilterDropped
        target = keep_row if kept else drop_row
        opposite = drop_row if kept else keep_row
        if opposite is not None:
            session.delete(opposite)

        if target is None:
            target = target_cls(
                doi=doi,
                decision_scope_hash=self.llm_decision_scope_hash,
                decision_scope_text=self.llm_decision_scope_text,
            )
            session.add(target)

        target.score = score
        target.reason = reason
        target.model_name = model_name
        target.prompt_tokens = usage.prompt_tokens
        target.completion_tokens = usage.completion_tokens
        target.total_tokens = usage.total_tokens
        target.decided_at = datetime.utcnow()
        session.flush()

    def _record_llm_usage(self, usage: LLMTokenUsage) -> None:
        self.llm_prompt_tokens_total += usage.prompt_tokens
        self.llm_completion_tokens_total += usage.completion_tokens
        self.llm_total_tokens_total += usage.total_tokens
        self.llm_api_calls += 1

    def _match_with_llm(
        self,
        record: ProviderRecord,
        *,
        session: Session | None = None,
        logger: FilterLog = None,
    ) -> tuple[bool, str]:
        doi = str(record.doi or "").strip().lower()
        if doi in self.llm_scores:
            score = self.llm_scores[doi]
            matched = score >= self.threshold
            return (True, "matched") if matched else (False, "query_llm_below_threshold")

        cached_keep = self.llm_cached_kept.get(doi) if self.llm_use_cached_keep else None
        if cached_keep is not None:
            self.llm_scores[doi] = cached_keep.score
            self.llm_reasons[doi] = cached_keep.reason
            self.llm_models[doi] = cached_keep.model_name
            self.llm_token_usages[doi] = LLMTokenUsage(
                prompt_tokens=cached_keep.prompt_tokens,
                completion_tokens=cached_keep.completion_tokens,
                total_tokens=cached_keep.total_tokens,
            )
            self.llm_cache_hits_kept += 1
            _emit(
                logger,
                "query 结果复核[llm]: "
                f"doi={record.doi or '-'} action=keep source=sqlite_keep_cache model={cached_keep.model_name or '-'} "
                f"score={cached_keep.score:.4f} reason={cached_keep.reason or '-'}",
            )
            return True, "matched"

        cached_drop = self.llm_cached_dropped.get(doi) if self.llm_use_cached_drop else None
        if cached_drop is not None:
            self.llm_scores[doi] = cached_drop.score
            self.llm_reasons[doi] = cached_drop.reason
            self.llm_models[doi] = cached_drop.model_name
            self.llm_token_usages[doi] = LLMTokenUsage(
                prompt_tokens=cached_drop.prompt_tokens,
                completion_tokens=cached_drop.completion_tokens,
                total_tokens=cached_drop.total_tokens,
            )
            self.llm_cache_hits_dropped += 1
            _emit(
                logger,
                "query 结果复核[llm]: "
                f"doi={record.doi or '-'} action=drop source=sqlite_drop_cache model={cached_drop.model_name or '-'} "
                f"score={cached_drop.score:.4f} reason={cached_drop.reason or '-'}",
            )
            return False, "query_llm_cached_drop"

        if self.client is None:
            return self._fallback_match(record, logger=logger, reason="LLM 客户端不可用")

        try:
            _emit(
                logger,
                "query 结果复核[llm]: "
                f"开始判定 doi={record.doi or '-'} active_model={self.llm_active_model or '-'} threshold={self.threshold:.4f}",
            )
            score, reason, usage, model_name = self._score_with_llm_model_fallback(record, logger=logger)
            self.llm_scores[doi] = score
            self.llm_reasons[doi] = reason
            self.llm_models[doi] = model_name
            self.llm_token_usages[doi] = usage
            self._record_llm_usage(usage)
            matched = score >= self.threshold
            if session is not None:
                self._persist_llm_decision(
                    session,
                    doi=doi,
                    kept=matched,
                    score=score,
                    reason=reason,
                    model_name=model_name,
                    usage=usage,
                )
            entry = LLMDecisionCacheEntry(
                doi=doi,
                kept=matched,
                score=score,
                reason=reason,
                model_name=model_name,
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens,
                total_tokens=usage.total_tokens,
                decided_at=datetime.utcnow(),
            )
            if matched:
                self.llm_cached_kept[doi] = entry
                self.llm_cached_dropped.pop(doi, None)
            else:
                self.llm_cached_dropped[doi] = entry
                self.llm_cached_kept.pop(doi, None)
            _emit(
                logger,
                "query 结果复核[llm]: "
                f"doi={record.doi or '-'} model={model_name or '-'} score={score:.4f} threshold={self.threshold:.4f} "
                f"prompt_tokens={usage.prompt_tokens} completion_tokens={usage.completion_tokens} total_tokens={usage.total_tokens} "
                f"action={'keep' if matched else 'drop'} reason={reason or '-'}",
            )
            return (True, "matched") if matched else (False, "query_llm_below_threshold")
        except Exception as exc:  # pragma: no cover - 网络容错
            return self._fallback_match(record, logger=logger, reason=f"LLM 判定失败: {exc}")

    def _fallback_match(
        self,
        record: ProviderRecord,
        *,
        logger: FilterLog = None,
        reason: str,
    ) -> tuple[bool, str]:
        if self.boolean_filter is not None:
            _emit(logger, f"query 结果复核: {reason}，当前记录回退为 boolean。")
            matched = self.boolean_filter.matches(_record_text(record, limit=12000).lower())
            return (True, "matched") if matched else (False, "query_boolean_filter_not_matched")
        _emit(logger, f"query 结果复核: {reason}，当前记录放行。")
        return True, "matched"

    def _fallback(self, logger: FilterLog, reason: str) -> None:
        if self.boolean_filter is not None:
            self.effective_mode = "boolean"
            _emit(logger, f"query 结果复核: {reason}，整体回退到 boolean。")
            return
        self.effective_mode = "none"
        _emit(logger, f"query 结果复核: {reason}，整体回退到 none。")


def build_query_filter_runtime(
    *,
    mode: str | None,
    threshold: float | None,
    raw_query: str,
    plan: QueryPlan,
    llm_scoring_prompt: str | None = None,
    llm_use_cached_keep: bool = True,
    llm_use_cached_drop: bool = True,
    logger: FilterLog = None,
) -> QueryFilterRuntime:
    requested_mode = str(mode or DEFAULT_QUERY_FILTER_MODE).strip().lower() or DEFAULT_QUERY_FILTER_MODE
    if requested_mode not in SUPPORTED_QUERY_FILTER_MODES:
        _emit(logger, f"query 结果复核: 未知模式 '{requested_mode}'，改用 {DEFAULT_QUERY_FILTER_MODE}。")
        requested_mode = DEFAULT_QUERY_FILTER_MODE

    try:
        normalized_threshold = float(threshold if threshold is not None else DEFAULT_EMBEDDING_THRESHOLD)
    except (TypeError, ValueError):
        normalized_threshold = DEFAULT_EMBEDDING_THRESHOLD
    normalized_threshold = min(max(normalized_threshold, 0.0), 1.0)

    boolean_filter = build_query_boolean_filter(plan)
    runtime = QueryFilterRuntime(
        requested_mode=requested_mode,
        effective_mode=requested_mode,
        threshold=normalized_threshold,
        raw_query=raw_query,
        plan=plan,
        boolean_filter=boolean_filter,
        llm_scoring_prompt=_resolve_llm_scoring_prompt(llm_scoring_prompt),
        llm_use_cached_keep=bool(llm_use_cached_keep),
        llm_use_cached_drop=bool(llm_use_cached_drop),
    )
    runtime.llm_model_candidates = _llm_model_candidates()
    runtime.llm_active_model = runtime.llm_model_candidates[0] if runtime.llm_model_candidates else _chat_model_name()
    runtime.llm_decision_scope_hash, runtime.llm_decision_scope_text = _llm_decision_scope(
        raw_query=raw_query,
        plan=plan,
        boolean_filter=boolean_filter,
        llm_scoring_prompt=runtime.llm_scoring_prompt,
    )

    if requested_mode == "none":
        _emit(logger, f"query 结果复核: {runtime.describe()}")
        return runtime

    if requested_mode == "boolean":
        if boolean_filter is None:
            runtime.effective_mode = "none"
            _emit(logger, "query 结果复核: boolean 模式未提取到可执行规则，回退到 none。")
        else:
            _emit(logger, f"query 结果复核: {runtime.describe()}")
        return runtime

    runtime.client = _create_openai_client()
    if runtime.client is None:
        runtime._fallback(logger, "AI 客户端不可用")
        _emit(logger, f"query 结果复核: {runtime.describe()}")
        return runtime

    if requested_mode == "embedding":
        runtime.embedding_query_text = build_query_embedding_text(plan)
        if not runtime.embedding_query_text:
            runtime._fallback(logger, "未提取出 embedding query 文本")
        _emit(logger, f"query 结果复核: {runtime.describe()}, query={runtime.embedding_query_text}")
        return runtime

    _emit(logger, "query 结果复核[llm]: 将按 query + domain objective 的相关度逐篇打分。")
    _emit(logger, f"query 结果复核: {runtime.describe()} (逐篇 LLM 打分)")
    return runtime
