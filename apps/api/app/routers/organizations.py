from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth_dependencies import Principal, require_path_organization
from app.db import get_session
from app.models import Organization
from app.schemas import OrganizationResponse

router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.get("/{organization_id}", response_model=OrganizationResponse)
async def get_organization(
    organization_id: UUID,
    principal: Principal = Depends(require_path_organization),
    session: AsyncSession = Depends(get_session),
) -> OrganizationResponse:
    organization = await session.get(Organization, organization_id)

    if organization is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="organization not found",
        )

    return OrganizationResponse(
        id=organization.id,
        name=organization.name,
        slug=organization.slug,
        role=principal.role,
    )
