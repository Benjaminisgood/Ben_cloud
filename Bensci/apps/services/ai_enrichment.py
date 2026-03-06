from __future__ import annotations

import json
import re
from collections.abc import Callable
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from apps.core.config import settings
from apps.db.models import Article
from apps.providers import ProviderRecord
from apps.services.article_service import touch_article_activity
from apps.services.doi_metadata import fetch_metadata_by_doi
from apps.services.normalizers import join_semicolon, split_semicolon
from apps.services.query_filtering import (
    _create_openai_client,
    _embedding_model_name,
    _embedding_vectors,
    _hash_text,
    _merged_record_text,
    _normalize_embedding_dimensions,
    _pack_embedding,
)

try:
    from openai import OpenAI
except Exception:  # pragma: no cover
    OpenAI = None  # type: ignore[assignment]

FillLog = Callable[[str], None] | None

FILLABLE_FIELDS = (
    "title",
    "keywords",
    "abstract",
    "journal",
    "corresponding_author",
    "affiliations",
    "source",
    "publisher",
    "published_date",
    "url",
)


def _log(logger: FillLog, message: str) -> None:
    if logger is not None:
        logger(message)


def _format_fields(fields: list[str]) -> str:
    if not fields:
        return "无"
    return ", ".join(fields)


def _is_empty(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, tuple, set)):
        return len(value) == 0
    return False


def _missing_fields(article: Article) -> list[str]:
    missing: list[str] = []
    if _is_empty(article.title):
        missing.append("title")
    if _is_empty(article.keywords):
        missing.append("keywords")
    if _is_empty(article.abstract):
        missing.append("abstract")
    if _is_empty(article.journal):
        missing.append("journal")
    if _is_empty(article.corresponding_author):
        missing.append("corresponding_author")
    if _is_empty(article.affiliations):
        missing.append("affiliations")
    if _is_empty(article.source):
        missing.append("source")
    if _is_empty(article.publisher):
        missing.append("publisher")
    if _is_empty(article.published_date):
        missing.append("published_date")
    if _is_empty(article.url):
        missing.append("url")
    return missing


def _assign_if_missing(article: Article, field: str, value: object) -> bool:
    if value in (None, "", [], ()):  # fast path
        return False

    if field == "keywords":
        if not _is_empty(article.keywords):
            return False
        values = [str(v).strip() for v in (value or []) if str(v).strip()]
        if not values:
            return False
        article.keywords = join_semicolon(values)
        return True

    if field == "affiliations":
        if not _is_empty(article.affiliations):
            return False
        values = [str(v).strip() for v in (value or []) if str(v).strip()]
        if not values:
            return False
        article.affiliations = join_semicolon(values)
        return True

    current = getattr(article, field)
    if not _is_empty(current):
        return False
    text = str(value).strip()
    if not text:
        return False
    setattr(article, field, text)
    return True


def _fetch_article_context(url: str) -> dict[str, str]:
    try:
        resp = requests.get(
            url,
            timeout=settings.request_timeout_seconds,
            headers={"User-Agent": settings.request_user_agent},
            allow_redirects=True,
        )
    except Exception:
        return {"url": url, "title": "", "text": ""}

    content_type = (resp.headers.get("content-type") or "").lower()
    final_url = str(resp.url)
    if "text/html" not in content_type:
        return {"url": final_url, "title": "", "text": ""}

    soup = BeautifulSoup(resp.text, "html.parser")
    title = (soup.title.text if soup.title and soup.title.text else "").strip()

    for selector in ("script", "style", "noscript"):
        for node in soup.select(selector):
            node.decompose()

    candidate_parts = []
    for selector in (
        "meta[name='description']",
        "meta[property='og:description']",
    ):
        meta = soup.select_one(selector)
        if meta and meta.get("content"):
            candidate_parts.append(str(meta.get("content")).strip())

    paragraphs = [p.get_text(" ", strip=True) for p in soup.select("p")]
    paragraphs = [p for p in paragraphs if len(p) > 40]
    candidate_parts.extend(paragraphs[:25])

    text = "\n".join(candidate_parts)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > 12000:
        text = text[:12000]

    return {"url": final_url, "title": title, "text": text}


def _parse_json_object(raw: str) -> dict[str, object]:
    if not raw:
        return {}
    raw = raw.strip()
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass

    match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
    if not match:
        return {}

    try:
        parsed = json.loads(match.group(0))
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


def _ai_fill_missing(
    article: Article,
    missing_fields: list[str],
    *,
    metadata_hint: dict[str, object],
    logger: FillLog,
) -> dict[str, object]:
    api_key = (settings.aliyun_ai_api_key or "").strip().strip("'\"")
    base_url = (settings.aliyun_ai_api_base_url or "").strip().strip("'\"")

    if not api_key:
        _log(logger, "AI key 未配置，跳过 AI 补全。")
        return {}
    if OpenAI is None:
        _log(logger, "openai SDK 不可用，跳过 AI 补全。")
        return {}

    url_candidates = []
    if article.url:
        url_candidates.append(article.url)
    url_candidates.append(f"https://doi.org/{article.doi}")

    context = {"url": "", "title": "", "text": ""}
    for candidate in url_candidates:
        ctx = _fetch_article_context(candidate)
        if ctx.get("text"):
            context = ctx
            break
        if not context.get("url"):
            context = ctx

    if not context.get("text") and not metadata_hint:
        _log(logger, "未获取到可读上下文，跳过 AI 补全。")
        return {}

    prompt = {
        "doi": article.doi,
        "missing_fields": missing_fields,
        "existing": {
            "title": article.title,
            "keywords": split_semicolon(article.keywords),
            "abstract": article.abstract,
            "journal": article.journal,
            "corresponding_author": article.corresponding_author,
            "affiliations": split_semicolon(article.affiliations),
            "source": article.source,
            "publisher": article.publisher,
            "published_date": article.published_date,
            "url": article.url,
            "citation_count": article.citation_count,
            "impact_factor": article.impact_factor,
        },
        "metadata_hint": metadata_hint,
        "article_context": {
            "url": context.get("url", ""),
            "title": context.get("title", ""),
            "text": context.get("text", ""),
        },
        "rules": [
            "Return JSON only. Do not add explanations.",
            "Only include fields listed in missing_fields.",
            "Do not guess. If a field is uncertain, omit it.",
            "Use YYYY-MM-DD for published_date when possible, otherwise YYYY-MM, otherwise YYYY.",
            "Return keywords and affiliations as arrays.",
        ],
    }

    model_name = (settings.aliyun_ai_model or "qwen-plus").strip().strip("'\"") or "qwen-plus"

    try:
        client = OpenAI(api_key=api_key, base_url=base_url)
        resp = client.chat.completions.create(
            model=model_name,
            temperature=0,
            messages=[
                {
                    "role": "system",
                    "content": "You are a rigorous scholarly-metadata extraction assistant.",
                },
                {
                    "role": "user",
                    "content": json.dumps(prompt, ensure_ascii=False),
                },
            ],
            response_format={"type": "json_object"},
        )
    except Exception as exc:  # pragma: no cover
        _log(logger, f"AI 请求失败: {exc}")
        return {}

    message = ""
    if resp.choices:
        message = str((resp.choices[0].message.content or "")).strip()

    data = _parse_json_object(message)
    if not data:
        _log(logger, "AI 返回为空或不可解析，跳过。")
        return {}
    return data


def _article_to_provider_record(article: Article) -> ProviderRecord:
    return ProviderRecord(
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
    )


def _fill_embedding_if_requested(article: Article, *, logger: FillLog) -> bool:
    client = _create_openai_client()
    if client is None:
        _log(logger, f"[{article.doi}] embedding 客户端不可用，跳过 embedding。")
        return False

    model_name = _embedding_model_name()
    dimensions = _normalize_embedding_dimensions(settings.aliyun_ai_embedding_dimensions)
    record = _article_to_provider_record(article)
    text = _merged_record_text(article, record)
    if not text:
        _log(logger, f"[{article.doi}] 无可用于 embedding 的文本，跳过 embedding。")
        return False

    text_hash = _hash_text(text)
    if (
        article.embedding_vector
        and article.embedding_model == model_name
        and int(article.embedding_dimensions or 0) == dimensions
        and article.embedding_text_hash == text_hash
    ):
        _log(logger, f"[{article.doi}] embedding 已是最新，跳过生成。")
        return False

    try:
        vector = _embedding_vectors(
            client,
            texts=[text],
            model_name=model_name,
            dimensions=dimensions,
        )[0]
    except Exception as exc:  # pragma: no cover
        _log(logger, f"[{article.doi}] embedding 生成失败: {exc}")
        return False

    article.embedding_vector = _pack_embedding(vector)
    article.embedding_model = model_name
    article.embedding_dimensions = dimensions
    article.embedding_text_hash = text_hash
    article.embedding_updated_at = datetime.utcnow()
    _log(logger, f"[{article.doi}] embedding 已生成/更新。")
    return True


def enrich_article_record(
    session: Session,
    article: Article,
    *,
    logger: FillLog = None,
    include_embedding: bool = False,
) -> dict[str, object]:
    result = {
        "article_id": article.id,
        "doi": article.doi,
        "skipped": False,
        "filled_fields": [],
        "metadata_filled": [],
        "ai_filled": [],
        "embedding_generated": False,
    }

    if article.check_status == "correct":
        result["skipped"] = True
        _log(logger, f"[{article.doi}] check_status=correct，跳过补全。")
        return result

    missing_before = _missing_fields(article)
    if not missing_before and not include_embedding:
        result["skipped"] = True
        _log(logger, f"[{article.doi}] 字段已完整，无需补全。")
        return result

    if missing_before:
        _log(logger, f"[{article.doi}] 开始补全（缺失: {_format_fields(missing_before)}）。")
    else:
        _log(logger, f"[{article.doi}] 字段完整，仅按请求处理 embedding。")

    metadata: dict[str, object] = {}
    if missing_before:
        metadata = fetch_metadata_by_doi(article.doi)
        for field in missing_before:
            if _assign_if_missing(article, field, metadata.get(field)):
                result["metadata_filled"].append(field)
        if result["metadata_filled"]:
            metadata_added = ", ".join(f"+{field}" for field in result["metadata_filled"])
            _log(logger, f"[{article.doi}] DOI 元数据补全: {metadata_added}")
        else:
            _log(logger, f"[{article.doi}] DOI 元数据未补出新字段。")

    missing_after_metadata = _missing_fields(article)
    if missing_after_metadata:
        _log(logger, f"[{article.doi}] 进入 AI 补全（仍缺失: {_format_fields(missing_after_metadata)}）。")
        ai_data = _ai_fill_missing(
            article,
            missing_after_metadata,
            metadata_hint=metadata,
            logger=logger,
        )
        for field in missing_after_metadata:
            if _assign_if_missing(article, field, ai_data.get(field)):
                result["ai_filled"].append(field)
        if result["ai_filled"]:
            ai_added = ", ".join(f"+{field}" for field in result["ai_filled"])
            _log(logger, f"[{article.doi}] AI 补全: {ai_added}")
        else:
            _log(logger, f"[{article.doi}] AI 未补全出新字段。")

    if not article.source:
        article.source = "ai-enriched"
        if "source" not in result["metadata_filled"] and "source" not in result["ai_filled"]:
            result["ai_filled"].append("source")

    if include_embedding:
        result["embedding_generated"] = _fill_embedding_if_requested(article, logger=logger)

    filled_fields = list(dict.fromkeys(result["metadata_filled"] + result["ai_filled"]))
    if result["embedding_generated"]:
        filled_fields.append("embedding")

    if not filled_fields:
        result["skipped"] = True
    else:
        touch_article_activity(article, when=datetime.utcnow())

    result["filled_fields"] = filled_fields
    _log(logger, f"[{article.doi}] 补全完成（新增: {_format_fields(filled_fields)}）。")
    return result


def enrich_article_by_id(
    session: Session,
    article_id: int,
    *,
    logger: FillLog = None,
    include_embedding: bool = False,
) -> dict[str, object]:
    article = session.get(Article, article_id)
    if article is None:
        return {
            "article_id": article_id,
            "skipped": True,
            "reason": "not_found",
            "filled_fields": [],
            "metadata_filled": [],
            "ai_filled": [],
            "embedding_generated": False,
        }

    return enrich_article_record(session, article, logger=logger, include_embedding=include_embedding)
