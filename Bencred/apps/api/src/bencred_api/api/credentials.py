"""Credential API routes."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from bencred_api.db.session import get_db
from bencred_api.repositories.credential import CredentialRepository
from bencred_api.services.credential import CredentialService
from bencred_api.schemas.credential import (
    CredentialCreate,
    CredentialWithSecret,
    CredentialListResponse,
    CredentialResponse,
    CredentialReview,
    CredentialUpdate,
)

router = APIRouter(prefix="/credentials", tags=["credentials"])


def get_credential_service(
    session: AsyncSession = Depends(get_db),
) -> CredentialService:
    """Dependency to get credential service."""
    repository = CredentialRepository(session)
    return CredentialService(repository)


@router.post("", response_model=CredentialResponse, status_code=201)
async def create_credential(
    data: CredentialCreate,
    service: CredentialService = Depends(get_credential_service),
) -> CredentialResponse:
    """Create a new credential with encrypted storage. Returns ID for audit trail."""
    return await service.create_credential(data)


@router.get("", response_model=CredentialListResponse)
async def list_credentials(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    category: str | None = Query(None, description="Filter by category"),
    is_active: bool | None = Query(None, description="Filter by active status"),
    review_status: str | None = Query(None, description="Filter by review status"),
    source: str | None = Query(None, description="Filter by record source"),
    service: CredentialService = Depends(get_credential_service),
) -> CredentialListResponse:
    """List credentials with pagination and filtering."""
    credentials, total = await service.list_credentials(
        page=page,
        page_size=page_size,
        category=category,
        is_active=is_active,
        review_status=review_status,
        source=source,
    )
    return CredentialListResponse(
        items=credentials,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{credential_id}", response_model=CredentialResponse)
async def get_credential(
    credential_id: int,
    service: CredentialService = Depends(get_credential_service),
) -> CredentialResponse:
    """Get credential by ID (without secret data)."""
    try:
        return await service.get_credential(credential_id, decrypt=False)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{credential_id}/secret", response_model=CredentialWithSecret)
async def get_credential_secret(
    credential_id: int,
    service: CredentialService = Depends(get_credential_service),
) -> CredentialWithSecret:
    """Get credential with decrypted secret data. Requires elevated permissions."""
    try:
        return await service.get_credential(credential_id, decrypt=True)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/{credential_id}", response_model=CredentialResponse)
async def update_credential(
    credential_id: int,
    data: CredentialUpdate,
    service: CredentialService = Depends(get_credential_service),
) -> CredentialResponse:
    """Update credential."""
    try:
        return await service.update_credential(credential_id, data)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{credential_id}", status_code=204)
async def delete_credential(
    credential_id: int,
    service: CredentialService = Depends(get_credential_service),
) -> None:
    """Delete credential."""
    deleted = await service.delete_credential(credential_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Credential not found")


@router.post("/{credential_id}/rotate", response_model=CredentialResponse)
async def rotate_credential(
    credential_id: int,
    new_secret: str,
    service: CredentialService = Depends(get_credential_service),
) -> CredentialResponse:
    """Rotate credential with new secret and update last_rotated timestamp."""
    try:
        return await service.rotate_credential(credential_id, new_secret)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{credential_id}/review", response_model=CredentialResponse)
async def review_credential(
    credential_id: int,
    data: CredentialReview,
    service: CredentialService = Depends(get_credential_service),
) -> CredentialResponse:
    """Review and approve/reject a credential submission."""
    try:
        return await service.review_credential(credential_id, data)
    except ValueError as e:
        status_code = 404 if "not found" in str(e).lower() else 400
        raise HTTPException(status_code=status_code, detail=str(e))
