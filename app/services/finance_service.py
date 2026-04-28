from datetime import date
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.finance import Expense, Goal, ExpenseCategory
from app.models.schedule import Schedule, Payment, ScheduleStatus
from app.schemas.finance import ExpenseCreate, ExpenseUpdate, GoalCreate, FinancialSummary


class FinanceService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Expenses ──────────────────────────────────────────────────────────────

    async def create_expense(self, data: ExpenseCreate) -> Expense:
        expense = Expense(**data.model_dump())
        self.db.add(expense)
        await self.db.flush()
        await self.db.refresh(expense)
        return expense

    async def get_expenses(
        self, start: date | None = None, end: date | None = None
    ) -> list[Expense]:
        query = select(Expense)
        if start:
            query = query.where(Expense.expense_date >= start)
        if end:
            query = query.where(Expense.expense_date <= end)
        result = await self.db.execute(query.order_by(Expense.expense_date.desc()))
        return list(result.scalars().all())

    async def update_expense(self, expense_id: UUID, data: ExpenseUpdate) -> Expense:
        result = await self.db.execute(select(Expense).where(Expense.id == expense_id))
        expense = result.scalar_one_or_none()
        if not expense:
            raise HTTPException(status_code=404, detail="Despesa não encontrada")
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(expense, field, value)
        await self.db.flush()
        return expense

    async def delete_expense(self, expense_id: UUID) -> None:
        result = await self.db.execute(select(Expense).where(Expense.id == expense_id))
        expense = result.scalar_one_or_none()
        if not expense:
            raise HTTPException(status_code=404, detail="Despesa não encontrada")
        await self.db.delete(expense)
        await self.db.flush()

    # ── Goals ─────────────────────────────────────────────────────────────────

    async def create_goal(self, data: GoalCreate) -> Goal:
        goal = Goal(**data.model_dump())
        self.db.add(goal)
        await self.db.flush()
        await self.db.refresh(goal)
        return goal

    async def get_goals(self) -> list[Goal]:
        result = await self.db.execute(
            select(Goal).order_by(Goal.reference_date.desc())
        )
        return list(result.scalars().all())

    # ── Financial Summary ─────────────────────────────────────────────────────

    async def get_summary(self, start: date, end: date) -> FinancialSummary:
        from datetime import datetime, timezone

        dt_start = datetime.combine(start, datetime.min.time()).replace(tzinfo=timezone.utc)
        dt_end = datetime.combine(end, datetime.max.time()).replace(tzinfo=timezone.utc)

        # Revenue from completed schedules
        sched_result = await self.db.execute(
            select(Schedule).where(
                and_(
                    Schedule.status == ScheduleStatus.COMPLETED,
                    Schedule.scheduled_at >= dt_start,
                    Schedule.scheduled_at <= dt_end,
                )
            )
        )
        completed = list(sched_result.scalars().all())
        total_revenue = sum(float(s.total_price) for s in completed)

        # Revenue breakdown by payment method
        pay_result = await self.db.execute(
            select(Payment).where(
                Payment.schedule_id.in_([s.id for s in completed])
            )
        )
        payments = list(pay_result.scalars().all())
        revenue_by_method: dict[str, float] = {}
        for p in payments:
            key = p.method.value
            revenue_by_method[key] = revenue_by_method.get(key, 0) + float(p.amount)

        # Expenses
        exp_result = await self.db.execute(
            select(func.sum(Expense.amount)).where(
                and_(
                    Expense.expense_date >= start,
                    Expense.expense_date <= end,
                )
            )
        )
        total_expenses = float(exp_result.scalar() or 0)

        return FinancialSummary(
            period_start=start,
            period_end=end,
            total_revenue=total_revenue,
            total_expenses=total_expenses,
            profit=total_revenue - total_expenses,
            revenue_by_payment_method=revenue_by_method,
            appointment_count=len(completed),
        )
