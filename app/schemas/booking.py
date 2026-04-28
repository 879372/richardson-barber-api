import uuid
from datetime import datetime, date
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator


# ─── Client Schemas ───────────────────────────────────────────────────────────

class ClientBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    phone: str = Field(..., min_length=8, max_length=20)
    email: str | None = None
    birthday: date | None = None
    notes: str | None = None


class ClientCreate(ClientBase):
    pass


class ClientUpdate(BaseModel):
    name: str | None = None
    email: str | None = None
    birthday: date | None = None
    notes: str | None = None


class ClientOut(ClientBase):
    id: uuid.UUID
    total_spent: float
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Service Schemas ──────────────────────────────────────────────────────────

class ServiceBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    description: str | None = None
    price: float = Field(..., gt=0)
    duration_minutes: int = Field(30, gt=0)
    is_active: bool = True
    display_order: int = 0


class ServiceCreate(ServiceBase):
    pass


class ServiceUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    price: float | None = None
    duration_minutes: int | None = None
    is_active: bool | None = None
    display_order: int | None = None


class ServiceOut(ServiceBase):
    id: uuid.UUID
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Schedule / Payment Schemas ───────────────────────────────────────────────

class PaymentMethod(str, Enum):
    PIX = "pix"
    CASH = "cash"
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    TRANSFER = "transfer"


class ScheduleStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


class PaymentIn(BaseModel):
    method: PaymentMethod
    amount: float = Field(..., gt=0)


class ScheduleCreate(BaseModel):
    client_id: uuid.UUID
    barber_id: uuid.UUID
    service_id: uuid.UUID
    scheduled_at: datetime
    notes: str | None = None


class ScheduleUpdate(BaseModel):
    status: ScheduleStatus | None = None
    notes: str | None = None
    scheduled_at: datetime | None = None


class CompleteScheduleRequest(BaseModel):
    payments: list[PaymentIn]

    @model_validator(mode="before")
    @classmethod
    def check_payments_not_empty(cls, values: Any) -> Any:
        payments = values.get("payments", [])
        if not payments:
            raise ValueError("Informe ao menos uma forma de pagamento")
        return values


class PaymentOut(BaseModel):
    id: uuid.UUID
    method: PaymentMethod
    amount: float
    paid_at: datetime

    model_config = {"from_attributes": True}


class ScheduleOut(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    barber_id: uuid.UUID
    service_id: uuid.UUID
    scheduled_at: datetime
    ends_at: datetime
    status: ScheduleStatus
    notes: str | None
    total_price: float
    payments: list[PaymentOut]
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Availability Schemas ─────────────────────────────────────────────────────

class AvailabilityCreate(BaseModel):
    week_day: int = Field(..., ge=0, le=6)
    start_time: str  # "HH:MM"
    end_time: str    # "HH:MM"
    is_active: bool = True


class AvailabilityOut(AvailabilityCreate):
    id: uuid.UUID
    barber_id: uuid.UUID

    model_config = {"from_attributes": True}


class TimeBlockCreate(BaseModel):
    start_at: datetime
    end_at: datetime
    reason: str | None = None


class TimeBlockOut(TimeBlockCreate):
    id: uuid.UUID
    barber_id: uuid.UUID
    created_at: datetime

    model_config = {"from_attributes": True}
