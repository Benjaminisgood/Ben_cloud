from __future__ import annotations

from datetime import datetime
from typing import Iterable, Literal

from sqlalchemy import asc, desc, func, or_, select, text
from sqlalchemy.orm import Session, selectinload

from apps.db.models import Article, Tag, article_tags
from apps.models.schemas import ArticleCreate, ArticleUpdate
from apps.providers.base import ProviderRecord
from apps.services.normalizers import join_semicolon, normalize_doi, normalize_list, split_semicolon

CheckStatus = Literal["unchecked", "correct", "error"]
SortBy = Literal["ingested_at", "published_date", "impact_factor"]
SortOrder = Literal["desc", "asc"]
TagMode = Literal["or", "and"]
CheckFilterMode = Literal["all", "hide_correct", "only_error"]


def _now_utc() -> datetime:
    return datetime.utcnow()


def _normalize_check_status(value: str | None) -> CheckStatus:
    normalized = (value or "unchecked").strip().lower()
    if normalized == "correct":
        return "correct"
    if normalized == "error":
        return "error"
    if normalized == "unchecked":
        return "unchecked"
    return "unchecked"


def _normalize_check_filter(value: str | None) -> CheckFilterMode:
    normalized = (value or "all").strip().lower()
    if normalized == "hide_correct":
        return "hide_correct"
    if normalized == "only_error":
        return "only_error"
    return "all"


def _normalized_check_status_expr():
    return func.coalesce(func.nullif(func.lower(Article.check_status), ""), "unchecked")


def _normalize_tag_names(tags: Iterable[str]) -> list[str]:
    normalized = []
    for tag in tags:
        text = str(tag).strip().lower()
        if text:
            normalized.append(text)
    return normalize_list(normalized)


def _build_fts_query(raw: str) -> str:
    tokens = [token.strip() for token in str(raw or "").split() if token.strip()]
    cleaned: list[str] = []
    for token in tokens:
        safe = token.replace('"', "")
        if safe:
            cleaned.append(f'"{safe}"')
    return " AND ".join(cleaned)


def get_or_create_tags(session: Session, tags: Iterable[str]) -> list[Tag]:
    tag_names = _normalize_tag_names(tags)
    if not tag_names:
        return []

    existing_tags = session.scalars(select(Tag).where(Tag.name.in_(tag_names))).all()
    existing_map = {tag.name: tag for tag in existing_tags}
    result = list(existing_tags)

    for name in tag_names:
        if name in existing_map:
            continue
        tag = Tag(name=name)
        session.add(tag)
        result.append(tag)

    session.flush()
    return result


def touch_article_activity(article: Article, *, when: datetime | None = None) -> None:
    stamp = when or _now_utc()
    article.ingested_at = stamp
    article.updated_at = stamp


def _replace_article_tags(session: Session, article: Article, tags: Iterable[str]) -> None:
    normalized_tags = _normalize_tag_names(tags)
    current_tags = sorted(tag.name for tag in article.tags)
    if current_tags == sorted(normalized_tags):
        return
    article.tags = get_or_create_tags(session, normalized_tags)


def article_to_read_dict(article: Article) -> dict:
    return {
        "id": article.id,
        "doi": article.doi,
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
        "note": article.note,
        "check_status": _normalize_check_status(article.check_status),
        "citation_count": article.citation_count,
        "impact_factor": article.impact_factor,
        "ingested_at": article.ingested_at,
        "tags": [{"id": tag.id, "name": tag.name} for tag in sorted(article.tags, key=lambda t: t.name)],
        "created_at": article.created_at,
        "updated_at": article.updated_at,
    }


def create_article(session: Session, payload: ArticleCreate) -> Article:
    doi = normalize_doi(payload.doi)
    if not doi:
        raise ValueError("DOI 不能为空")

    existing = session.scalar(select(Article).where(Article.doi == doi))
    if existing is not None:
        raise ValueError(f"DOI 已存在: {doi}")

    article = Article(
        doi=doi,
        title=payload.title.strip(),
        keywords=join_semicolon(payload.keywords),
        abstract=payload.abstract.strip(),
        journal=payload.journal.strip(),
        corresponding_author=payload.corresponding_author.strip(),
        affiliations=join_semicolon(payload.affiliations),
        source=payload.source.strip(),
        publisher=payload.publisher.strip(),
        published_date=payload.published_date.strip(),
        url=payload.url.strip(),
        note=payload.note.strip(),
        check_status=_normalize_check_status(payload.check_status),
        citation_count=payload.citation_count,
        impact_factor=payload.impact_factor,
    )
    article.tags = get_or_create_tags(session, payload.tags)
    session.add(article)
    session.flush()
    return article


def update_article(session: Session, article: Article, payload: ArticleUpdate) -> Article:
    updates = payload.model_dump(exclude_unset=True)

    for field in (
        "title",
        "abstract",
        "journal",
        "corresponding_author",
        "source",
        "publisher",
        "published_date",
        "url",
        "note",
    ):
        if field in updates and updates[field] is not None:
            setattr(article, field, str(updates[field]).strip())

    if "keywords" in updates:
        article.keywords = join_semicolon(updates.get("keywords"))

    if "affiliations" in updates:
        article.affiliations = join_semicolon(updates.get("affiliations"))

    if "check_status" in updates:
        article.check_status = _normalize_check_status(str(updates.get("check_status") or "unchecked"))

    if "citation_count" in updates:
        article.citation_count = updates.get("citation_count")

    if "impact_factor" in updates:
        article.impact_factor = updates.get("impact_factor")

    if "tags" in updates:
        _replace_article_tags(session, article, updates.get("tags") or [])

    if session.is_modified(article, include_collections=True):
        touch_article_activity(article)

    session.flush()
    return article


def delete_article(session: Session, article: Article) -> None:
    session.delete(article)
    session.flush()


def get_article_or_none(session: Session, article_id: int) -> Article | None:
    return session.scalar(select(Article).options(selectinload(Article.tags)).where(Article.id == article_id))


def list_articles(
    session: Session,
    *,
    search: str | None,
    source: str | None,
    journal: str | None,
    tags: Iterable[str] | None,
    offset: int,
    limit: int,
    tags_and: Iterable[str] | None = None,
    tags_or: Iterable[str] | None = None,
    tag_mode: TagMode = "or",
    check_status: CheckStatus | None = None,
    check_filter: CheckFilterMode = "all",
    sort_by: SortBy = "ingested_at",
    sort_order: SortOrder = "desc",
) -> tuple[list[Article], int]:
    filtered_ids_stmt = _build_filtered_id_stmt(
        search=search,
        source=source,
        journal=journal,
        tags=tags,
        tags_and=tags_and,
        tags_or=tags_or,
        tag_mode=tag_mode,
        check_status=check_status,
        check_filter=check_filter,
    )
    distinct_ids = filtered_ids_stmt.subquery()
    total = session.scalar(select(func.count()).select_from(distinct_ids)) or 0

    ids = _load_sorted_article_ids(
        session,
        distinct_ids_subquery=distinct_ids,
        sort_by=sort_by,
        sort_order=sort_order,
        offset=offset,
        limit=limit,
    )
    if not ids:
        return [], total

    items = _load_articles_by_ids(session, ids)
    return items, total


def list_articles_for_export(
    session: Session,
    *,
    search: str | None,
    source: str | None,
    journal: str | None,
    tags: Iterable[str] | None,
    tags_and: Iterable[str] | None = None,
    tags_or: Iterable[str] | None = None,
    tag_mode: TagMode = "or",
    check_status: CheckStatus | None = None,
    check_filter: CheckFilterMode = "all",
    sort_by: SortBy = "ingested_at",
    sort_order: SortOrder = "desc",
) -> list[Article]:
    filtered_ids_stmt = _build_filtered_id_stmt(
        search=search,
        source=source,
        journal=journal,
        tags=tags,
        tags_and=tags_and,
        tags_or=tags_or,
        tag_mode=tag_mode,
        check_status=check_status,
        check_filter=check_filter,
    )
    distinct_ids = filtered_ids_stmt.subquery()
    ids = _load_sorted_article_ids(
        session,
        distinct_ids_subquery=distinct_ids,
        sort_by=sort_by,
        sort_order=sort_order,
        offset=0,
        limit=None,
    )
    if not ids:
        return []
    return _load_articles_by_ids(session, ids)


def _build_filtered_id_stmt(
    *,
    search: str | None,
    source: str | None,
    journal: str | None,
    tags: Iterable[str] | None,
    tags_and: Iterable[str] | None = None,
    tags_or: Iterable[str] | None = None,
    tag_mode: TagMode = "or",
    check_status: CheckStatus | None = None,
    check_filter: CheckFilterMode = "all",
):
    base_stmt = select(Article.id).select_from(Article)

    legacy_tags = _normalize_tag_names(tags or [])
    normalized_tags_and = _normalize_tag_names(tags_and or [])
    normalized_tags_or = _normalize_tag_names(tags_or or [])
    if legacy_tags:
        if tag_mode == "and":
            normalized_tags_and = normalize_list([*normalized_tags_and, *legacy_tags])
        else:
            normalized_tags_or = normalize_list([*normalized_tags_or, *legacy_tags])

    if normalized_tags_and:
        tagged_all_ids_stmt = (
            select(article_tags.c.article_id)
            .join(Tag, Tag.id == article_tags.c.tag_id)
            .where(Tag.name.in_(normalized_tags_and))
            .group_by(article_tags.c.article_id)
            .having(func.count(func.distinct(Tag.name)) == len(normalized_tags_and))
        )
        base_stmt = base_stmt.where(Article.id.in_(tagged_all_ids_stmt))

    if normalized_tags_or:
        tagged_any_ids_stmt = (
            select(article_tags.c.article_id)
            .join(Tag, Tag.id == article_tags.c.tag_id)
            .where(Tag.name.in_(normalized_tags_or))
        )
        base_stmt = base_stmt.where(Article.id.in_(tagged_any_ids_stmt))

    if source:
        base_stmt = base_stmt.where(func.lower(Article.source) == source.strip().lower())

    if journal:
        pattern = f"%{journal.strip().lower()}%"
        base_stmt = base_stmt.where(func.lower(Article.journal).like(pattern))

    normalized_status_expr = _normalized_check_status_expr()
    if check_status:
        base_stmt = base_stmt.where(normalized_status_expr == check_status.lower())
    else:
        effective_check_filter = _normalize_check_filter(check_filter)
        if effective_check_filter == "hide_correct":
            base_stmt = base_stmt.where(normalized_status_expr != "correct")
        elif effective_check_filter == "only_error":
            base_stmt = base_stmt.where(normalized_status_expr == "error")

    if search:
        fts_query = _build_fts_query(search)
        note_pattern = f"%{search.strip().lower()}%"
        if fts_query:
            base_stmt = base_stmt.where(
                or_(
                    Article.id.in_(
                        select(text("article_id"))
                        .select_from(text("articles_fts"))
                        .where(text("articles_fts MATCH :fts_query"))
                        .params(fts_query=fts_query)
                    ),
                    func.lower(func.coalesce(Article.note, "")).like(note_pattern),
                )
            )
        else:
            pattern = f"%{search.strip().lower()}%"
            base_stmt = base_stmt.where(
                or_(
                    func.lower(Article.doi).like(pattern),
                    func.lower(Article.title).like(pattern),
                    func.lower(Article.abstract).like(pattern),
                    func.lower(Article.keywords).like(pattern),
                    func.lower(Article.corresponding_author).like(pattern),
                    func.lower(Article.affiliations).like(pattern),
                    func.lower(func.coalesce(Article.note, "")).like(pattern),
                )
            )

    return base_stmt.distinct()


def _load_sorted_article_ids(
    session: Session,
    *,
    distinct_ids_subquery,
    sort_by: SortBy,
    sort_order: SortOrder,
    offset: int = 0,
    limit: int | None = None,
) -> list[int]:
    if sort_by == "published_date":
        sort_col = func.coalesce(Article.published_date, "")
    elif sort_by == "impact_factor":
        sort_col = func.coalesce(Article.impact_factor, -1.0)
    else:
        sort_col = Article.ingested_at

    order_expr = asc(sort_col) if sort_order == "asc" else desc(sort_col)

    paged_ids_stmt = (
        select(Article.id)
        .where(Article.id.in_(select(distinct_ids_subquery.c.id)))
        .order_by(order_expr, Article.id.desc())
    )
    if offset > 0:
        paged_ids_stmt = paged_ids_stmt.offset(offset)
    if limit is not None:
        paged_ids_stmt = paged_ids_stmt.limit(limit)
    return list(session.scalars(paged_ids_stmt))


def _load_articles_by_ids(session: Session, ids: list[int]) -> list[Article]:
    items = session.scalars(
        select(Article)
        .options(selectinload(Article.tags))
        .where(Article.id.in_(ids))
    ).all()

    order_map = {article_id: idx for idx, article_id in enumerate(ids)}
    items.sort(key=lambda item: order_map.get(item.id, 10**9))
    return items


def list_tags(
    session: Session,
    *,
    search: str | None = None,
    include_counts: bool = False,
) -> list[Tag] | list[tuple[Tag, int]]:
    if include_counts:
        article_count = func.count(article_tags.c.article_id).label("article_count")
        stmt = (
            select(Tag, article_count)
            .outerjoin(article_tags, article_tags.c.tag_id == Tag.id)
            .group_by(Tag.id, Tag.name)
            .order_by(desc(article_count), Tag.name.asc())
        )
        if search:
            stmt = stmt.where(func.lower(Tag.name).like(f"%{search.strip().lower()}%"))
        rows = session.execute(stmt).all()
        return [(row[0], int(row[1] or 0)) for row in rows]

    stmt = select(Tag).order_by(Tag.name.asc())
    if search:
        stmt = stmt.where(func.lower(Tag.name).like(f"%{search.strip().lower()}%"))
    return session.scalars(stmt).all()


def upsert_provider_record(session: Session, record: ProviderRecord, save_tags: Iterable[str] | None = None) -> str:
    doi = normalize_doi(record.doi)
    if not doi:
        return "skipped"

    target = session.scalar(select(Article).options(selectinload(Article.tags)).where(Article.doi == doi))

    if target is None:
        target = Article(doi=doi, check_status="unchecked")
        session.add(target)
        status = "inserted"
    else:
        status = "updated"

    if record.title:
        target.title = record.title
    if record.abstract and len(record.abstract) >= len(target.abstract or ""):
        target.abstract = record.abstract
    if record.journal:
        target.journal = record.journal
    if record.corresponding_author:
        target.corresponding_author = record.corresponding_author
    if record.source:
        target.source = record.source
    if record.publisher:
        target.publisher = record.publisher
    if record.published_date:
        target.published_date = record.published_date
    if record.url:
        target.url = record.url
    if record.citation_count is not None:
        target.citation_count = max(record.citation_count, 0)
    if record.impact_factor is not None:
        target.impact_factor = max(float(record.impact_factor), 0.0)

    existing_keywords = split_semicolon(target.keywords)
    target.keywords = join_semicolon(existing_keywords + (record.keywords or []))

    existing_affiliations = split_semicolon(target.affiliations)
    target.affiliations = join_semicolon(existing_affiliations + (record.affiliations or []))

    extra_tags = list(save_tags or [])
    if extra_tags:
        combined = [tag.name for tag in target.tags] + extra_tags
        _replace_article_tags(session, target, combined)

    if status == "updated" and session.is_modified(target, include_collections=True):
        touch_article_activity(target)

    session.flush()
    return status
