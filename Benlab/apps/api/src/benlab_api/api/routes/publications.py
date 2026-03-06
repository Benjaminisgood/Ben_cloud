"""文献/论文管理 API 路由"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from benlab_api.db.session import get_db
from benlab_api.models.publication import Publication
from benlab_api.services.publication_downloader import PublicationDownloader

router = APIRouter(prefix="/api/publications", tags=["publications"])


class PublicationCreate(BaseModel):
    doi: str = Field(..., description="DOI 号", min_length=1)
    title: str = Field(..., description="文章标题", min_length=1, max_length=500)
    authors: str = Field(default="", description="作者列表（JSON 数组或逗号分隔）")
    journal: str = Field(default="", description="期刊/会议名称", max_length=255)
    publication_year: int | None = Field(default=None, description="出版年份")
    abstract: str = Field(default="", description="摘要")
    notes: str = Field(default="", description="备注")


class PublicationUpdate(BaseModel):
    title: str | None = Field(default=None, description="文章标题", max_length=500)
    authors: str | None = Field(default=None, description="作者列表")
    journal: str | None = Field(default=None, description="期刊/会议名称", max_length=255)
    publication_year: int | None = Field(default=None, description="出版年份")
    abstract: str | None = Field(default=None, description="摘要")
    notes: str | None = Field(default=None, description="备注")


class PublicationResponse(BaseModel):
    id: int
    doi: str
    title: str
    authors: str
    journal: str
    publication_year: int | None
    abstract: str
    pdf_path: str | None
    pdf_downloaded: bool
    download_status: str
    download_error: str | None
    metadata_source: str
    notes: str
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class PublicationListResponse(BaseModel):
    items: list[PublicationResponse]
    total: int
    has_more: bool


@router.get("", response_model=PublicationListResponse, summary="获取文献列表")
def list_publications(
    db: Annotated[Session, Depends(get_db)],
    q: Annotated[str | None, Query(description="搜索关键词（标题/DOI）")] = None,
    status_filter: Annotated[str | None, Query(description="下载状态过滤")] = None,
    before_id: Annotated[int | None, Query(description="分页：此 ID 之前的记录")] = None,
    limit: Annotated[int, Query(ge=1, le=200, description="每页数量")] = 50,
):
    """获取文献列表，支持搜索和分页"""
    query = select(Publication)

    if q:
        query = query.where(
            (Publication.title.ilike(f"%{q}%")) | (Publication.doi.ilike(f"%{q}%"))
        )

    if status_filter:
        query = query.where(Publication.download_status == status_filter)

    if before_id:
        query = query.where(Publication.id < before_id)

    query = query.order_by(Publication.id.desc()).limit(limit + 1)

    results = db.execute(query).scalars().all()
    has_more = len(results) > limit
    items = results[:limit] if has_more else results

    return PublicationListResponse(
        items=[PublicationResponse.model_validate(item) for item in items],
        total=len(items),
        has_more=has_more,
    )


@router.get("/{publication_id}", response_model=PublicationResponse, summary="获取文献详情")
def get_publication(
    publication_id: int,
    db: Annotated[Session, Depends(get_db)],
):
    """获取单篇文献的详细信息"""
    publication = db.get(Publication, publication_id)
    if not publication:
        raise HTTPException(status_code=404, detail="文献不存在")
    return PublicationResponse.model_validate(publication)


@router.post("", response_model=PublicationResponse, status_code=status.HTTP_201_CREATED, summary="创建文献")
def create_publication(
    data: PublicationCreate,
    db: Annotated[Session, Depends(get_db)],
):
    """创建新的文献记录"""
    # 检查 DOI 是否已存在
    existing = db.execute(select(Publication).where(Publication.doi == data.doi)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail=f"DOI {data.doi} 已存在")

    publication = Publication(
        doi=data.doi,
        title=data.title,
        authors=data.authors,
        journal=data.journal,
        publication_year=data.publication_year,
        abstract=data.abstract,
        notes=data.notes,
        metadata_source="manual",
    )
    db.add(publication)
    db.commit()
    db.refresh(publication)
    return PublicationResponse.model_validate(publication)


@router.put("/{publication_id}", response_model=PublicationResponse, summary="更新文献")
def update_publication(
    publication_id: int,
    data: PublicationUpdate,
    db: Annotated[Session, Depends(get_db)],
):
    """更新文献信息"""
    publication = db.get(Publication, publication_id)
    if not publication:
        raise HTTPException(status_code=404, detail="文献不存在")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(publication, field, value)

    db.commit()
    db.refresh(publication)
    return PublicationResponse.model_validate(publication)


@router.delete("/{publication_id}", status_code=status.HTTP_204_NO_CONTENT, summary="删除文献")
def delete_publication(
    publication_id: int,
    db: Annotated[Session, Depends(get_db)],
):
    """删除文献记录"""
    publication = db.get(Publication, publication_id)
    if not publication:
        raise HTTPException(status_code=404, detail="文献不存在")

    db.delete(publication)
    db.commit()
    return None


@router.post("/{publication_id}/download", response_model=PublicationResponse, summary="下载 PDF")
def download_pdf(
    publication_id: int,
    db: Annotated[Session, Depends(get_db)],
    force: Annotated[bool, Query(description="强制重新下载")] = False,
):
    """通过 DOI 下载文献 PDF 文件"""
    publication = db.get(Publication, publication_id)
    if not publication:
        raise HTTPException(status_code=404, detail="文献不存在")

    if publication.pdf_downloaded and not force:
        raise HTTPException(status_code=400, detail="PDF 已下载，使用 force=true 强制重新下载")

    downloader = PublicationDownloader()
    result = downloader.download_by_doi(publication.doi, publication.id)

    if result["success"]:
        publication.pdf_path = result["pdf_path"]
        publication.pdf_downloaded = True
        publication.download_status = "success"
        publication.download_error = None
    else:
        publication.download_status = "failed"
        publication.download_error = result.get("error", "未知错误")

    db.commit()
    db.refresh(publication)
    return PublicationResponse.model_validate(publication)


@router.post("/batch-download", response_model=dict, summary="批量下载 PDF")
def batch_download(
    db: Annotated[Session, Depends(get_db)],
    status_filter: Annotated[str | None, Query(description="只下载特定状态的文献")] = "pending",
    limit: Annotated[int, Query(ge=1, le=100, description="批量下载数量限制")] = 10,
):
    """批量下载文献 PDF"""
    query = select(Publication).where(Publication.download_status != "success")
    if status_filter:
        query = query.where(Publication.download_status == status_filter)
    query = query.order_by(Publication.id.asc()).limit(limit)

    publications = db.execute(query).scalars().all()

    downloader = PublicationDownloader()
    results = {"success": 0, "failed": 0, "details": []}

    for pub in publications:
        result = downloader.download_by_doi(pub.doi, pub.id)
        if result["success"]:
            pub.pdf_path = result["pdf_path"]
            pub.pdf_downloaded = True
            pub.download_status = "success"
            pub.download_error = None
            results["success"] += 1
        else:
            pub.download_status = "failed"
            pub.download_error = result.get("error", "未知错误")
            results["failed"] += 1

        results["details"].append({
            "id": pub.id,
            "doi": pub.doi,
            "success": result["success"],
            "error": result.get("error"),
        })
        db.commit()

    return results


@router.get("/stats", summary="获取统计信息")
def get_stats(
    db: Annotated[Session, Depends(get_db)],
):
    """获取文献统计信息"""
    from sqlalchemy import func

    total = db.scalar(select(func.count(Publication.id)))
    downloaded = db.scalar(select(func.count(Publication.id)).where(Publication.pdf_downloaded == True))
    pending = db.scalar(select(func.count(Publication.id)).where(Publication.download_status == "pending"))
    failed = db.scalar(select(func.count(Publication.id)).where(Publication.download_status == "failed"))

    return {
        "total": total or 0,
        "downloaded": downloaded or 0,
        "pending": pending or 0,
        "failed": failed or 0,
        "success_rate": round((downloaded or 0) / (total or 1) * 100, 2),
    }
