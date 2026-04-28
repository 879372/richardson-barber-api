from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, extract
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.models.client import Client
from app.models.user import User, UserRole
from app.schemas.booking import ClientCreate, ClientUpdate, ClientOut

router = APIRouter(prefix="/clients", tags=["clients"])


@router.post("/", response_model=ClientOut, status_code=status.HTTP_201_CREATED)
async def create_client(data: ClientCreate, db: AsyncSession = Depends(get_db)):
    """Public endpoint — auto-creates client on first booking."""
    existing = await db.execute(select(Client).where(Client.phone == data.phone))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Telefone já cadastrado")
    client = Client(**data.model_dump())
    db.add(client)
    await db.flush()
    await db.refresh(client)
    return client


@router.get("/", response_model=list[ClientOut])
async def list_clients(
    search: str | None = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Client)
    if search:
        query = query.where(
            Client.name.ilike(f"%{search}%") | Client.phone.ilike(f"%{search}%")
        )
    result = await db.execute(query.order_by(Client.name).limit(limit).offset(offset))
    return list(result.scalars().all())


@router.get("/birthdays", response_model=list[ClientOut])
async def birthdays_today(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return clients with birthday today or this week."""
    from datetime import date
    today = date.today()
    result = await db.execute(
        select(Client).where(
            extract("month", Client.birthday) == today.month,
            extract("day", Client.birthday) == today.day,
        )
    )
    return list(result.scalars().all())


@router.get("/{client_id}", response_model=ClientOut)
async def get_client(
    client_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Client).where(Client.id == client_id))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    return client


@router.put("/{client_id}", response_model=ClientOut)
async def update_client(
    client_id: UUID,
    data: ClientUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Client).where(Client.id == client_id))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(client, field, value)
    await db.flush()
    return client
