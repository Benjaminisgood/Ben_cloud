from fastapi import APIRouter

from apps.models.schemas import ProviderRead
from apps.providers import get_all_providers

router = APIRouter(prefix="/providers", tags=["providers"])


@router.get("", response_model=list[ProviderRead])
def list_providers() -> list[ProviderRead]:
    providers = get_all_providers()
    return [
        ProviderRead(
            key=provider.key,
            title=provider.title,
            configured=provider.is_configured(),
            description=provider.description,
        )
        for provider in providers.values()
    ]
