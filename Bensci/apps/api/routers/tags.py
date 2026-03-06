from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from apps.api.deps import get_db
from apps.db.models import Tag
from apps.models.schemas import TagCreate, TagListResponse, TagRead
from apps.services.article_service import list_tags

router = APIRouter(prefix="/tags", tags=["tags"])


@router.get("", response_model=TagListResponse)
def get_tags(
    search: str | None = Query(default=None),
    include_counts: bool = Query(default=True, description="是否返回标签关联文献数量"),
    db: Session = Depends(get_db),
) -> TagListResponse:
    if include_counts:
        rows = list_tags(db, search=search, include_counts=True)
        items = [TagRead(id=tag.id, name=tag.name, article_count=count) for tag, count in rows]
        return TagListResponse(total=len(items), items=items)

    raw_tags = list_tags(db, search=search, include_counts=False)
    return TagListResponse(total=len(raw_tags), items=[TagRead.model_validate(item) for item in raw_tags])


@router.post("", response_model=TagRead, status_code=status.HTTP_201_CREATED)
def create_tag(payload: TagCreate, db: Session = Depends(get_db)) -> TagRead:
    name = payload.name.strip().lower()
    if not name:
        raise HTTPException(status_code=400, detail="标签名不能为空")

    existing = db.scalar(select(Tag).where(Tag.name == name))
    if existing is not None:
        return TagRead(id=existing.id, name=existing.name, article_count=len(existing.articles))

    tag = Tag(name=name)
    db.add(tag)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        duplicate = db.scalar(select(Tag).where(Tag.name == name))
        if duplicate:
            return TagRead(id=duplicate.id, name=duplicate.name, article_count=len(duplicate.articles))
        raise

    db.refresh(tag)
    return TagRead(id=tag.id, name=tag.name, article_count=0)


@router.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tag(tag_id: int, db: Session = Depends(get_db)) -> None:
    tag = db.get(Tag, tag_id)
    if tag is None:
        raise HTTPException(status_code=404, detail="标签不存在")
    db.delete(tag)
    db.commit()
