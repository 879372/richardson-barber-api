import uuid
from datetime import datetime, timezone
from enum import Enum

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ExpenseCategory(str, Enum):
    FIXED = "fixed"
    VARIABLE = "variable"


class Expense(Base):
    __tablename__ = "expenses"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    description: Mapped[str] = mapped_column(sa.String(255))
    amount: Mapped[float] = mapped_column(sa.Numeric(10, 2))
    category: Mapped[ExpenseCategory] = mapped_column(
        sa.Enum(ExpenseCategory), default=ExpenseCategory.VARIABLE
    )
    expense_date: Mapped[datetime] = mapped_column(sa.Date)
    notes: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class Goal(Base):
    __tablename__ = "goals"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    period: Mapped[str] = mapped_column(sa.String(10))  # "daily" | "weekly" | "monthly"
    target_amount: Mapped[float] = mapped_column(sa.Numeric(10, 2))
    reference_date: Mapped[datetime] = mapped_column(sa.Date)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
