"""Link repository for database operations."""
from datetime import datetime
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from benlink_api.models.link import Link
from benlink_api.schemas.link import LinkCreate, LinkUpdate


class LinkRepository:
    """Repository for link database operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, data: LinkCreate) -> Link:
        """Create a new link. Returns ID for audit trail."""
        link = Link(
            url=data.url,
            title=data.title,
            description=data.description,
            category=data.category,
            tags=",".join(data.tags) if data.tags else None,
            notes=data.notes,
            source=data.source,
            source_detail=data.source_detail,
            review_status=data.review_status,
            status=data.status,
            priority=data.priority,
        )
        self.session.add(link)
        await self.session.flush()
        return link
    
    async def get_by_id(self, link_id: int) -> Link | None:
        """Get link by ID."""
        result = await self.session.execute(
            select(Link).where(Link.id == link_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_url(self, url: str) -> Link | None:
        """Get link by URL."""
        result = await self.session.execute(
            select(Link).where(Link.url == url)
        )
        return result.scalar_one_or_none()
    
    async def get_all(
        self,
        page: int = 1,
        page_size: int = 20,
        category: str | None = None,
        status: str | None = None,
        is_favorite: bool | None = None,
        tag: str | None = None,
        review_status: str | None = None,
        source: str | None = None,
    ) -> tuple[list[Link], int]:
        """Get paginated link list."""
        query = select(Link)
        count_query = select(func.count(Link.id))
        
        if category:
            query = query.where(Link.category == category)
            count_query = count_query.where(Link.category == category)
        
        if status:
            query = query.where(Link.status == status)
            count_query = count_query.where(Link.status == status)
        
        if is_favorite is not None:
            query = query.where(Link.is_favorite == is_favorite)
            count_query = count_query.where(Link.is_favorite == is_favorite)
        
        if tag:
            query = query.where(Link.tags.like(f"%{tag}%"))
            count_query = count_query.where(Link.tags.like(f"%{tag}%"))

        if review_status:
            query = query.where(Link.review_status == review_status)
            count_query = count_query.where(Link.review_status == review_status)

        if source:
            query = query.where(Link.source == source)
            count_query = count_query.where(Link.source == source)
        
        # Get total count
        total_result = await self.session.execute(count_query)
        total = total_result.scalar()
        
        # Get paginated results
        query = query.offset((page - 1) * page_size).limit(page_size).order_by(Link.created_at.desc())
        result = await self.session.execute(query)
        links = result.scalars().all()
        
        return list(links), total
    
    async def update(self, link_id: int, data: LinkUpdate) -> Link | None:
        """Update link. Returns updated link."""
        link = await self.get_by_id(link_id)
        if not link:
            return None
        
        update_data = data.model_dump(exclude_unset=True)
        if "tags" in update_data and update_data["tags"] is not None:
            update_data["tags"] = ",".join(update_data["tags"])
        
        for field, value in update_data.items():
            setattr(link, field, value)
        
        link.updated_at = datetime.utcnow()
        await self.session.flush()
        return link
    
    async def delete(self, link_id: int) -> bool:
        """Delete link. Returns True if deleted."""
        link = await self.get_by_id(link_id)
        if not link:
            return False
        
        await self.session.delete(link)
        await self.session.flush()
        return True
    
    async def update_accessed_at(self, link_id: int) -> None:
        """Update last accessed timestamp."""
        link = await self.get_by_id(link_id)
        if link:
            link.accessed_at = datetime.utcnow()
            await self.session.flush()
    
    async def update_last_checked(self, link_id: int) -> None:
        """Update last checked timestamp."""
        link = await self.get_by_id(link_id)
        if link:
            link.last_checked_at = datetime.utcnow()
            await self.session.flush()
