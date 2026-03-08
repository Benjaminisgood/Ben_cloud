"""Credential repository for database operations."""
from datetime import datetime
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from bencred_api.models.credential import Credential
from bencred_api.schemas.credential import CredentialCreate, CredentialUpdate


class CredentialRepository:
    """Repository for credential database operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, data: CredentialCreate) -> Credential:
        """Create a new credential. Returns ID for audit trail."""
        credential = Credential(
            name=data.name,
            credential_type=data.credential_type,
            encrypted_data=data.secret_data,  # Will be encrypted by service layer
            service_name=data.service_name,
            username=data.username,
            endpoint=data.endpoint,
            category=data.category,
            tags=",".join(data.tags) if data.tags else None,
            rotation_reminder_days=data.rotation_reminder_days,
            source=data.source,
            source_detail=data.source_detail,
            review_status=data.review_status,
            sensitivity=data.sensitivity,
            agent_access=data.agent_access,
        )
        self.session.add(credential)
        await self.session.flush()  # Get ID before commit
        return credential
    
    async def get_by_id(self, credential_id: int) -> Credential | None:
        """Get credential by ID."""
        result = await self.session.execute(
            select(Credential).where(Credential.id == credential_id)
        )
        return result.scalar_one_or_none()
    
    async def get_all(
        self,
        page: int = 1,
        page_size: int = 20,
        category: str | None = None,
        is_active: bool | None = None,
        review_status: str | None = None,
        source: str | None = None,
    ) -> tuple[list[Credential], int]:
        """Get paginated credential list."""
        query = select(Credential)
        count_query = select(func.count(Credential.id))
        
        if category:
            query = query.where(Credential.category == category)
            count_query = count_query.where(Credential.category == category)
        
        if is_active is not None:
            query = query.where(Credential.is_active == is_active)
            count_query = count_query.where(Credential.is_active == is_active)

        if review_status:
            query = query.where(Credential.review_status == review_status)
            count_query = count_query.where(Credential.review_status == review_status)

        if source:
            query = query.where(Credential.source == source)
            count_query = count_query.where(Credential.source == source)
        
        # Get total count
        total_result = await self.session.execute(count_query)
        total = total_result.scalar()
        
        # Get paginated results
        query = query.offset((page - 1) * page_size).limit(page_size).order_by(Credential.created_at.desc())
        result = await self.session.execute(query)
        credentials = result.scalars().all()
        
        return list(credentials), total
    
    async def update(self, credential_id: int, data: CredentialUpdate) -> Credential | None:
        """Update credential. Returns updated credential."""
        credential = await self.get_by_id(credential_id)
        if not credential:
            return None
        
        update_data = data.model_dump(exclude_unset=True)
        if "tags" in update_data and update_data["tags"] is not None:
            update_data["tags"] = ",".join(update_data["tags"])
        if "secret_data" in update_data:
            update_data["encrypted_data"] = update_data.pop("secret_data")

        for field, value in update_data.items():
            setattr(credential, field, value)
        
        credential.updated_at = datetime.utcnow()
        await self.session.flush()
        return credential
    
    async def delete(self, credential_id: int) -> bool:
        """Delete credential. Returns True if deleted."""
        credential = await self.get_by_id(credential_id)
        if not credential:
            return False
        
        await self.session.delete(credential)
        await self.session.flush()
        return True
    
    async def update_accessed_at(self, credential_id: int) -> None:
        """Update last accessed timestamp."""
        credential = await self.get_by_id(credential_id)
        if credential:
            credential.accessed_at = datetime.utcnow()
            await self.session.flush()
    
    async def update_last_rotated(self, credential_id: int) -> None:
        """Update last rotated timestamp."""
        credential = await self.get_by_id(credential_id)
        if credential:
            credential.last_rotated = datetime.utcnow()
            credential.updated_at = datetime.utcnow()
            await self.session.flush()
