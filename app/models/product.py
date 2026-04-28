import uuid
from datetime import datetime, timezone

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Product(Base):
    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(sa.String(150))
    brand: Mapped[str | None] = mapped_column(sa.String(100), nullable=True)
    stock_quantity: Mapped[int] = mapped_column(sa.Integer, default=0)
    min_stock_alert: Mapped[int] = mapped_column(sa.Integer, default=5)
    unit_cost: Mapped[float] = mapped_column(sa.Numeric(10, 2), default=0)
    sale_price: Mapped[float] = mapped_column(sa.Numeric(10, 2), default=0)
    is_active: Mapped[bool] = mapped_column(sa.Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    stock_movements: Mapped[list["StockMovement"]] = relationship(
        "StockMovement", back_populates="product"
    )


class StockMovement(Base):
    __tablename__ = "stock_movements"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), sa.ForeignKey("products.id"), index=True
    )
    movement_type: Mapped[str] = mapped_column(sa.String(20))  # "in" | "out"
    quantity: Mapped[int] = mapped_column(sa.Integer)
    reason: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    schedule_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.UUID(as_uuid=True), sa.ForeignKey("schedules.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    product: Mapped["Product"] = relationship("Product", back_populates="stock_movements")
