from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.models.service import Service
from app.models.user import User, UserRole
from app.schemas.booking import ServiceCreate, ServiceUpdate, ServiceOut

router = APIRouter(prefix="/services", tags=["services"])


@router.get("/", response_model=list[ServiceOut])
async def list_services(db: AsyncSession = Depends(get_db)):
    """Public — clients use this on the booking portal."""
    result = await db.execute(
        select(Service)
        .where(Service.is_active == True)
        .order_by(Service.display_order)
    )
    return list(result.scalars().all())


@router.get("/all", response_model=list[ServiceOut])
async def list_all_services(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Service).order_by(Service.display_order))
    return list(result.scalars().all())


@router.post("/", response_model=ServiceOut, status_code=status.HTTP_201_CREATED)
async def create_service(
    data: ServiceCreate,
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    service = Service(**data.model_dump())
    db.add(service)
    await db.flush()
    await db.refresh(service)
    return service


@router.put("/{service_id}", response_model=ServiceOut)
async def update_service(
    service_id: UUID,
    data: ServiceUpdate,
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Service).where(Service.id == service_id))
    service = result.scalar_one_or_none()
    if not service:
        raise HTTPException(status_code=404, detail="Serviço não encontrado")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(service, field, value)
    await db.flush()
    return service


@router.delete("/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_service(
    service_id: UUID,
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Service).where(Service.id == service_id))
    service = result.scalar_one_or_none()
    if not service:
        raise HTTPException(status_code=404, detail="Serviço não encontrado")
    service.is_active = False
    await db.flush()


@router.patch("/reorder", status_code=status.HTTP_204_NO_CONTENT)
async def reorder_services(
    order: list[dict],  # [{"id": "...", "display_order": 0}, ...]
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    for item in order:
        result = await db.execute(select(Service).where(Service.id == item["id"]))
        service = result.scalar_one_or_none()
        if service:
            service.display_order = item["display_order"]
    await db.flush()
