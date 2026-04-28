import uuid
from datetime import datetime, date
from enum import Enum

from pydantic import BaseModel, Field


# ─── Finance Schemas ──────────────────────────────────────────────────────────

class ExpenseCategory(str, Enum):
    FIXED = "fixed"
    VARIABLE = "variable"


class ExpenseCreate(BaseModel):
    description: str = Field(..., min_length=2, max_length=255)
    amount: float = Field(..., gt=0)
    category: ExpenseCategory = ExpenseCategory.VARIABLE
    expense_date: date
    notes: str | None = None


class ExpenseUpdate(BaseModel):
    description: str | None = None
    amount: float | None = None
    category: ExpenseCategory | None = None
    expense_date: date | None = None
    notes: str | None = None


class ExpenseOut(ExpenseCreate):
    id: uuid.UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class GoalCreate(BaseModel):
    period: str = Field(..., pattern="^(daily|weekly|monthly)$")
    target_amount: float = Field(..., gt=0)
    reference_date: date


class GoalOut(GoalCreate):
    id: uuid.UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class FinancialSummary(BaseModel):
    period_start: date
    period_end: date
    total_revenue: float
    total_expenses: float
    profit: float
    revenue_by_payment_method: dict[str, float]
    appointment_count: int


# ─── Product Schemas ──────────────────────────────────────────────────────────

class ProductCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    brand: str | None = None
    stock_quantity: int = Field(0, ge=0)
    min_stock_alert: int = Field(5, ge=0)
    unit_cost: float = Field(0, ge=0)
    sale_price: float = Field(0, ge=0)
    is_active: bool = True


class ProductUpdate(BaseModel):
    name: str | None = None
    brand: str | None = None
    min_stock_alert: int | None = None
    unit_cost: float | None = None
    sale_price: float | None = None
    is_active: bool | None = None


class ProductOut(ProductCreate):
    id: uuid.UUID
    created_at: datetime
    is_low_stock: bool = False

    model_config = {"from_attributes": True}


class StockMovementCreate(BaseModel):
    movement_type: str = Field(..., pattern="^(in|out)$")
    quantity: int = Field(..., gt=0)
    reason: str | None = None
    schedule_id: uuid.UUID | None = None


class StockMovementOut(StockMovementCreate):
    id: uuid.UUID
    product_id: uuid.UUID
    created_at: datetime

    model_config = {"from_attributes": True}
