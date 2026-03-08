"""Credential service for business logic and encryption."""
import base64
from datetime import datetime
from cryptography.fernet import Fernet
from bencred_api.core.config import get_settings
from bencred_api.repositories.credential import CredentialRepository
from bencred_api.schemas.credential import (
    CredentialCreate,
    CredentialResponse,
    CredentialReview,
    CredentialUpdate,
    CredentialWithSecret,
)
from bencred_api.models.credential import Credential

settings = get_settings()


class CredentialService:
    """Service for credential business logic."""

    VALID_REVIEW_STATUS = {"pending", "approved", "rejected", "archived"}
    VALID_AGENT_ACCESS = {"read", "masked", "approval_required", "deny"}
    VALID_SENSITIVITY = {"low", "medium", "high", "critical"}
    
    def __init__(self, repository: CredentialRepository):
        self.repository = repository
        # Use Fernet for symmetric encryption
        # In production, derive key from secure key management system
        try:
            self.fernet = Fernet(settings.FERNET_KEY.encode())
        except Exception:
            # If key is invalid, use a default for development
            self.fernet = Fernet(Fernet.generate_key())
    
    def _encrypt_data(self, data: str) -> str:
        """Encrypt secret data."""
        encrypted = self.fernet.encrypt(data.encode())
        return base64.urlsafe_b64encode(encrypted).decode()
    
    def _decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt secret data."""
        try:
            decoded = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted = self.fernet.decrypt(decoded)
            return decrypted.decode()
        except Exception as e:
            raise ValueError(f"Failed to decrypt data: {e}")

    def _credential_response(self, credential: Credential) -> CredentialResponse:
        """Normalize ORM data into the API response shape."""
        return CredentialResponse(
            id=credential.id,
            name=credential.name,
            credential_type=credential.credential_type,
            service_name=credential.service_name,
            username=credential.username,
            endpoint=credential.endpoint,
            category=credential.category,
            tags=credential.tags.split(",") if credential.tags else None,
            is_active=credential.is_active,
            source=credential.source,
            source_detail=credential.source_detail,
            review_status=credential.review_status,
            review_notes=credential.review_notes,
            reviewed_by=credential.reviewed_by,
            reviewed_at=credential.reviewed_at,
            sensitivity=credential.sensitivity,
            agent_access=credential.agent_access,
            last_rotated=credential.last_rotated,
            rotation_reminder_days=credential.rotation_reminder_days,
            created_at=credential.created_at,
            updated_at=credential.updated_at,
            accessed_at=credential.accessed_at,
        )

    def _validate_review_state(
        self,
        review_status: str | None = None,
        agent_access: str | None = None,
        sensitivity: str | None = None,
    ) -> None:
        if review_status and review_status not in self.VALID_REVIEW_STATUS:
            raise ValueError(f"Invalid review status: {review_status}")
        if agent_access and agent_access not in self.VALID_AGENT_ACCESS:
            raise ValueError(f"Invalid agent access: {agent_access}")
        if sensitivity and sensitivity not in self.VALID_SENSITIVITY:
            raise ValueError(f"Invalid sensitivity: {sensitivity}")
    
    async def create_credential(self, data: CredentialCreate) -> CredentialResponse:
        """Create a new credential with encrypted storage."""
        self._validate_review_state(
            review_status=data.review_status,
            agent_access=data.agent_access,
            sensitivity=data.sensitivity,
        )

        # Encrypt the secret data
        encrypted_data = self._encrypt_data(data.secret_data)
        
        # Create credential with encrypted data
        create_data = CredentialCreate(
            name=data.name,
            credential_type=data.credential_type,
            secret_data=encrypted_data,  # Store encrypted
            service_name=data.service_name,
            username=data.username,
            endpoint=data.endpoint,
            category=data.category,
            tags=data.tags,
            rotation_reminder_days=data.rotation_reminder_days,
            source=data.source,
            source_detail=data.source_detail,
            review_status=data.review_status,
            sensitivity=data.sensitivity,
            agent_access=data.agent_access,
        )
        
        credential = await self.repository.create(create_data)
        await self.repository.update_accessed_at(credential.id)
        
        return self._credential_response(credential)
    
    async def get_credential(self, credential_id: int, decrypt: bool = False) -> CredentialResponse | CredentialWithSecret:
        """Get credential by ID. Optionally decrypt secret data."""
        credential = await self.repository.get_by_id(credential_id)
        if not credential:
            raise ValueError(f"Credential {credential_id} not found")
        
        await self.repository.update_accessed_at(credential_id)
        
        if decrypt:
            decrypted_data = self._decrypt_data(credential.encrypted_data)
            return CredentialWithSecret(
                id=credential.id,
                name=credential.name,
                credential_type=credential.credential_type,
                service_name=credential.service_name,
                username=credential.username,
                endpoint=credential.endpoint,
                category=credential.category,
                tags=credential.tags.split(",") if credential.tags else None,
                is_active=credential.is_active,
                source=credential.source,
                source_detail=credential.source_detail,
                review_status=credential.review_status,
                review_notes=credential.review_notes,
                reviewed_by=credential.reviewed_by,
                reviewed_at=credential.reviewed_at,
                sensitivity=credential.sensitivity,
                agent_access=credential.agent_access,
                last_rotated=credential.last_rotated,
                rotation_reminder_days=credential.rotation_reminder_days,
                created_at=credential.created_at,
                updated_at=credential.updated_at,
                accessed_at=credential.accessed_at,
                decrypted_data=decrypted_data,
            )
        
        return self._credential_response(credential)
    
    async def list_credentials(
        self,
        page: int = 1,
        page_size: int = 20,
        category: str | None = None,
        is_active: bool | None = None,
        review_status: str | None = None,
        source: str | None = None,
    ) -> tuple[list[CredentialResponse], int]:
        """List credentials with pagination."""
        self._validate_review_state(review_status=review_status)
        credentials, total = await self.repository.get_all(
            page=page,
            page_size=page_size,
            category=category,
            is_active=is_active,
            review_status=review_status,
            source=source,
        )
        return [self._credential_response(c) for c in credentials], total

    async def update_credential(self, credential_id: int, data: CredentialUpdate) -> CredentialResponse:
        """Update credential."""
        self._validate_review_state(
            review_status=data.review_status,
            agent_access=data.agent_access,
            sensitivity=data.sensitivity,
        )

        # Encrypt new secret data if provided
        if data.secret_data:
            update_dict = data.model_dump()
            update_dict["secret_data"] = self._encrypt_data(data.secret_data)
            data = CredentialUpdate(**update_dict)
        
        credential = await self.repository.update(credential_id, data)
        if not credential:
            raise ValueError(f"Credential {credential_id} not found")

        return self._credential_response(credential)

    async def review_credential(
        self,
        credential_id: int,
        data: CredentialReview,
    ) -> CredentialResponse:
        """Apply a review decision to a credential record."""
        self._validate_review_state(
            review_status=data.review_status,
            agent_access=data.agent_access,
            sensitivity=data.sensitivity,
        )
        update_payload: dict[str, object] = {
            "review_status": data.review_status,
            "is_active": data.is_active if data.is_active is not None else data.review_status != "archived",
        }
        if data.review_notes is not None:
            update_payload["review_notes"] = data.review_notes
        if data.reviewed_by is not None:
            update_payload["reviewed_by"] = data.reviewed_by
        if data.sensitivity is not None:
            update_payload["sensitivity"] = data.sensitivity
        if data.agent_access is not None:
            update_payload["agent_access"] = data.agent_access

        update_data = CredentialUpdate(**update_payload)
        credential = await self.repository.update(credential_id, update_data)
        if not credential:
            raise ValueError(f"Credential {credential_id} not found")

        credential.reviewed_at = datetime.utcnow()
        credential.updated_at = datetime.utcnow()
        await self.repository.session.flush()
        return self._credential_response(credential)
    
    async def delete_credential(self, credential_id: int) -> bool:
        """Delete credential."""
        return await self.repository.delete(credential_id)
    
    async def rotate_credential(self, credential_id: int, new_secret: str) -> CredentialResponse:
        """Rotate credential with new secret."""
        encrypted_data = self._encrypt_data(new_secret)
        update_data = CredentialUpdate(secret_data=encrypted_data)
        
        credential = await self.repository.update(credential_id, update_data)
        if not credential:
            raise ValueError(f"Credential {credential_id} not found")
        
        await self.repository.update_last_rotated(credential_id)
        return self._credential_response(credential)
