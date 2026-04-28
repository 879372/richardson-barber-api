from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.models.user import User, UserRole
from app.schemas.finance import (
    ExpenseCreate, ExpenseUpdate, ExpenseOut,
    GoalCreate, GoalOut, FinancialSummary,
    ProductCreate, ProductUpdate, ProductOut,
    StockMovementCreate, StockMovementOut,
)
from app.services.finance_service import FinanceService
from sqlalchemy import select
from app.models.product import Product, StockMovement
from fastapi import HTTPException

router = APIRouter(prefix="/finance", tags=["finance"])


# ── Expenses ──────────────────────────────────────────────────────────────────

@router.get("/expenses", response_model=list[ExpenseOut])
async def list_expenses(
    start: date | None = Query(None),
    end: date | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = FinanceService(db)
    return await svc.get_expenses(start, end)


@router.post("/expenses", response_model=ExpenseOut, status_code=201)
async def create_expense(
    data: ExpenseCreate,
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.RECEPTIONIST)),
    db: AsyncSession = Depends(get_db),
):
    svc = FinanceService(db)
    return await svc.create_expense(data)


@router.put("/expenses/{expense_id}", response_model=ExpenseOut)
async def update_expense(
    expense_id: UUID,
    data: ExpenseUpdate,
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    svc = FinanceService(db)
    return await svc.update_expense(expense_id, data)


@router.delete("/expenses/{expense_id}", status_code=204)
async def delete_expense(
    expense_id: UUID,
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    svc = FinanceService(db)
    await svc.delete_expense(expense_id)


# ── Goals ─────────────────────────────────────────────────────────────────────

@router.get("/goals", response_model=list[GoalOut])
async def list_goals(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = FinanceService(db)
    return await svc.get_goals()


@router.post("/goals", response_model=GoalOut, status_code=201)
async def create_goal(
    data: GoalCreate,
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    svc = FinanceService(db)
    return await svc.create_goal(data)


# ── Summary ───────────────────────────────────────────────────────────────────

@router.get("/summary", response_model=FinancialSummary)
async def financial_summary(
    start: date = Query(...),
    end: date = Query(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = FinanceService(db)
    return await svc.get_summary(start, end)


# ── Products ──────────────────────────────────────────────────────────────────

@router.get("/products", response_model=list[ProductOut])
async def list_products(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Product).where(Product.is_active == True))
    products = list(result.scalars().all())
    out = []
    for p in products:
        data = ProductOut.model_validate(p)
        data.is_low_stock = p.stock_quantity <= p.min_stock_alert
        out.append(data)
    return out


@router.post("/products", response_model=ProductOut, status_code=201)
async def create_product(
    data: ProductCreate,
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    product = Product(**data.model_dump())
    db.add(product)
    await db.flush()
    await db.refresh(product)
    return product


@router.put("/products/{product_id}", response_model=ProductOut)
async def update_product(
    product_id: UUID,
    data: ProductUpdate,
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(product, field, value)
    await db.flush()
    return product


@router.post("/products/{product_id}/stock", response_model=StockMovementOut, status_code=201)
async def add_stock_movement(
    product_id: UUID,
    data: StockMovementCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Produto não encontrado")

    if data.movement_type == "out" and product.stock_quantity < data.quantity:
        raise HTTPException(status_code=400, detail="Estoque insuficiente")

    movement = StockMovement(
        product_id=product_id,
        movement_type=data.movement_type,
        quantity=data.quantity,
        reason=data.reason,
        schedule_id=data.schedule_id,
    )
    db.add(movement)

    if data.movement_type == "in":
        product.stock_quantity += data.quantity
    else:
        product.stock_quantity -= data.quantity

    await db.flush()
    await db.refresh(movement)
    return movement
