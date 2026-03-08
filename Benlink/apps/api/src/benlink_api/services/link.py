"""Link service for business logic and metadata fetching."""
from datetime import datetime
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import httpx
from benlink_api.core.config import get_settings
from benlink_api.repositories.link import LinkRepository
from benlink_api.schemas.link import LinkCreate, LinkResponse, LinkReview, LinkUpdate
from benlink_api.models.link import Link

settings = get_settings()


class LinkService:
    """Service for link business logic."""

    VALID_REVIEW_STATUS = {"pending", "approved", "rejected", "archived"}
    
    def __init__(self, repository: LinkRepository):
        self.repository = repository

    def _link_response(self, link: Link) -> LinkResponse:
        """Normalize ORM data into the API response shape."""
        return LinkResponse(
            id=link.id,
            url=link.url,
            title=link.title,
            description=link.description,
            category=link.category,
            tags=link.tags.split(",") if link.tags else None,
            notes=link.notes,
            status=link.status,
            priority=link.priority,
            source=link.source,
            source_detail=link.source_detail,
            review_status=link.review_status,
            review_notes=link.review_notes,
            reviewed_by=link.reviewed_by,
            reviewed_at=link.reviewed_at,
            domain=link.domain,
            favicon_url=link.favicon_url,
            og_image=link.og_image,
            is_active=link.is_active,
            is_favorite=link.is_favorite,
            created_at=link.created_at,
            updated_at=link.updated_at,
            accessed_at=link.accessed_at,
            last_checked_at=link.last_checked_at,
        )

    def _validate_review_status(self, review_status: str | None) -> None:
        if review_status and review_status not in self.VALID_REVIEW_STATUS:
            raise ValueError(f"Invalid review status: {review_status}")
    
    async def _fetch_metadata(self, url: str) -> dict:
        """Fetch Open Graph metadata from URL."""
        try:
            async with httpx.AsyncClient(
                timeout=settings.FETCH_TIMEOUT,
                follow_redirects=True,
                max_redirects=settings.MAX_REDIRECTS,
            ) as client:
                response = await client.get(url)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Extract metadata
                title = None
                description = None
                og_image = None
                favicon_url = None
                
                # Open Graph tags
                og_title = soup.find('meta', property='og:title')
                if og_title and og_title.get('content'):
                    title = og_title['content']
                
                og_desc = soup.find('meta', property='og:description')
                if og_desc and og_desc.get('content'):
                    description = og_desc['content']
                
                og_img = soup.find('meta', property='og:image')
                if og_img and og_img.get('content'):
                    og_image = og_img['content']
                
                # Fallback to regular meta tags
                if not title:
                    title_tag = soup.find('title')
                    if title_tag:
                        title = title_tag.get_text(strip=True)
                
                if not description:
                    desc_tag = soup.find('meta', attrs={'name': 'description'})
                    if desc_tag and desc_tag.get('content'):
                        description = desc_tag['content']
                
                # Favicon
                favicon = soup.find('link', rel=lambda x: x and 'icon' in x.lower() if isinstance(x, str) else False)
                if favicon and favicon.get('href'):
                    favicon_url = favicon['href']
                    if not favicon_url.startswith('http'):
                        parsed = urlparse(url)
                        favicon_url = f"{parsed.scheme}://{parsed.netloc}{favicon_url}"
                
                # Domain
                domain = urlparse(url).netloc
                
                return {
                    "title": title,
                    "description": description,
                    "og_image": og_image,
                    "favicon_url": favicon_url,
                    "domain": domain,
                }
        except Exception as e:
            # Return partial data on error
            parsed = urlparse(url)
            return {
                "title": None,
                "description": None,
                "og_image": None,
                "favicon_url": None,
                "domain": parsed.netloc,
            }
    
    async def create_link(self, data: LinkCreate, fetch_metadata: bool = True) -> LinkResponse:
        """Create a new link. Optionally fetch metadata from URL."""
        self._validate_review_status(data.review_status)

        # Check if URL already exists
        existing = await self.repository.get_by_url(data.url)
        if existing:
            raise ValueError(f"Link with URL {data.url} already exists")
        
        # Fetch metadata if requested
        metadata = {}
        if fetch_metadata:
            metadata = await self._fetch_metadata(data.url)
        
        # Create link
        create_data = LinkCreate(
            url=data.url,
            title=data.title or metadata.get("title"),
            description=data.description or metadata.get("description"),
            category=data.category,
            tags=data.tags,
            notes=data.notes,
            source=data.source,
            source_detail=data.source_detail,
            review_status=data.review_status,
            status=data.status,
            priority=data.priority,
        )
        
        link = await self.repository.create(create_data)
        
        # Update with fetched metadata
        if metadata:
            link.domain = metadata.get("domain")
            link.favicon_url = metadata.get("favicon_url")
            link.og_image = metadata.get("og_image")
            await self.repository.session.flush()

        await self.repository.update_accessed_at(link.id)
        
        return self._link_response(link)
    
    async def get_link(self, link_id: int) -> LinkResponse:
        """Get link by ID."""
        link = await self.repository.get_by_id(link_id)
        if not link:
            raise ValueError(f"Link {link_id} not found")
        
        await self.repository.update_accessed_at(link_id)
        
        return self._link_response(link)
    
    async def list_links(
        self,
        page: int = 1,
        page_size: int = 20,
        category: str | None = None,
        status: str | None = None,
        is_favorite: bool | None = None,
        tag: str | None = None,
        review_status: str | None = None,
        source: str | None = None,
    ) -> tuple[list[LinkResponse], int]:
        """List links with pagination and filtering."""
        self._validate_review_status(review_status)
        links, total = await self.repository.get_all(
            page=page,
            page_size=page_size,
            category=category,
            status=status,
            is_favorite=is_favorite,
            tag=tag,
            review_status=review_status,
            source=source,
        )
        return [self._link_response(l) for l in links], total
    
    async def update_link(self, link_id: int, data: LinkUpdate) -> LinkResponse:
        """Update link."""
        self._validate_review_status(data.review_status)
        link = await self.repository.update(link_id, data)
        if not link:
            raise ValueError(f"Link {link_id} not found")
        
        return self._link_response(link)

    async def review_link(self, link_id: int, data: LinkReview) -> LinkResponse:
        """Apply a review decision to a link record."""
        self._validate_review_status(data.review_status)
        update_payload: dict[str, object] = {
            "review_status": data.review_status,
            "is_active": data.is_active if data.is_active is not None else data.review_status not in {"rejected", "archived"},
        }
        if data.review_notes is not None:
            update_payload["review_notes"] = data.review_notes
        if data.reviewed_by is not None:
            update_payload["reviewed_by"] = data.reviewed_by
        if data.category is not None:
            update_payload["category"] = data.category
        if data.priority is not None:
            update_payload["priority"] = data.priority
        if data.status is not None:
            update_payload["status"] = data.status
        if data.is_favorite is not None:
            update_payload["is_favorite"] = data.is_favorite

        update_data = LinkUpdate(**update_payload)
        link = await self.repository.update(link_id, update_data)
        if not link:
            raise ValueError(f"Link {link_id} not found")

        link.reviewed_at = datetime.utcnow()
        link.updated_at = datetime.utcnow()
        await self.repository.session.flush()
        return self._link_response(link)
    
    async def delete_link(self, link_id: int) -> bool:
        """Delete link."""
        return await self.repository.delete(link_id)
    
    async def refresh_metadata(self, link_id: int) -> LinkResponse:
        """Refresh metadata for a link."""
        link = await self.repository.get_by_id(link_id)
        if not link:
            raise ValueError(f"Link {link_id} not found")
        
        metadata = await self._fetch_metadata(link.url)
        
        link.title = metadata.get("title") or link.title
        link.description = metadata.get("description") or link.description
        link.og_image = metadata.get("og_image")
        link.favicon_url = metadata.get("favicon_url")
        link.domain = metadata.get("domain")
        link.last_checked_at = None  # Will be set by update_last_checked
        
        await self.repository.session.flush()
        await self.repository.update_last_checked(link_id)
        
        return self._link_response(link)
    
    async def mark_favorite(self, link_id: int, is_favorite: bool) -> LinkResponse:
        """Mark link as favorite or unfavorite."""
        update_data = LinkUpdate(is_favorite=is_favorite)
        return await self.update_link(link_id, update_data)
    
    async def update_status(self, link_id: int, status: str) -> LinkResponse:
        """Update link reading status."""
        if status not in ["unread", "reading", "read", "archived"]:
            raise ValueError(f"Invalid status: {status}")
        
        update_data = LinkUpdate(status=status)
        return await self.update_link(link_id, update_data)
