from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, extract
from app.database import get_db
from app.models.user import User
from app.models.transaction import Transaction
from app.models.category import Category
from app.middleware.auth import get_current_user
from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel

router = APIRouter(prefix="/analytics", tags=["Analytics"])


class SummaryResponse(BaseModel):
    total_income: Decimal
    total_expense: Decimal
    balance: Decimal
    month: int
    year: int


class CategoryBreakdown(BaseModel):
    category_id: str
    category_name: str
    color: str
    icon: str
    total: Decimal
    percentage: float


class MonthlyData(BaseModel):
    month: int
    year: int
    income: Decimal
    expense: Decimal


class DailyData(BaseModel):
    date: str
    income: Decimal
    expense: Decimal


@router.get("/summary", response_model=SummaryResponse)
async def get_summary(
    month: int = Query(default=datetime.now().month, ge=1, le=12),
    year: int = Query(default=datetime.now().year),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    base_query = select(func.sum(Transaction.amount)).where(
        Transaction.user_id == current_user.id,
        extract("month", Transaction.date) == month,
        extract("year", Transaction.date) == year,
    )

    income_result = await db.execute(base_query.where(Transaction.type == "income"))
    expense_result = await db.execute(base_query.where(Transaction.type == "expense"))

    total_income = income_result.scalar() or Decimal("0")
    total_expense = expense_result.scalar() or Decimal("0")

    return SummaryResponse(
        total_income=total_income,
        total_expense=total_expense,
        balance=total_income - total_expense,
        month=month,
        year=year,
    )


@router.get("/by-category", response_model=list[CategoryBreakdown])
async def get_by_category(
    type: str = "expense",
    month: int = Query(default=datetime.now().month, ge=1, le=12),
    year: int = Query(default=datetime.now().year),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(
            Category.id,
            Category.name,
            Category.color,
            Category.icon,
            func.sum(Transaction.amount).label("total"),
        )
        .join(Transaction, Transaction.category_id == Category.id)
        .where(
            Transaction.user_id == current_user.id,
            Transaction.type == type,
            extract("month", Transaction.date) == month,
            extract("year", Transaction.date) == year,
        )
        .group_by(Category.id, Category.name, Category.color, Category.icon)
        .order_by(func.sum(Transaction.amount).desc())
    )

    rows = result.all()
    grand_total = sum(r.total for r in rows) or Decimal("1")

    return [
        CategoryBreakdown(
            category_id=r.id,
            category_name=r.name,
            color=r.color,
            icon=r.icon,
            total=r.total,
            percentage=round(float(r.total / grand_total * 100), 2),
        )
        for r in rows
    ]


@router.get("/monthly-trends", response_model=list[MonthlyData])
async def get_monthly_trends(
    months: int = Query(6, ge=1, le=24),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(
            extract("year", Transaction.date).label("year"),
            extract("month", Transaction.date).label("month"),
            Transaction.type,
            func.sum(Transaction.amount).label("total"),
        )
        .where(Transaction.user_id == current_user.id)
        .group_by("year", "month", Transaction.type)
        .order_by("year", "month")
    )

    rows = result.all()
    data: dict[tuple, dict] = {}
    for r in rows:
        key = (int(r.year), int(r.month))
        if key not in data:
            data[key] = {"income": Decimal("0"), "expense": Decimal("0")}
        data[key][r.type] = r.total

    return [
        MonthlyData(month=k[1], year=k[0], income=v["income"], expense=v["expense"])
        for k, v in sorted(data.items())
    ][-months:]


@router.get("/daily", response_model=list[DailyData])
async def get_daily(
    month: int = Query(default=datetime.now().month, ge=1, le=12),
    year: int = Query(default=datetime.now().year),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(
            Transaction.date,
            Transaction.type,
            func.sum(Transaction.amount).label("total"),
        )
        .where(
            Transaction.user_id == current_user.id,
            extract("month", Transaction.date) == month,
            extract("year", Transaction.date) == year,
        )
        .group_by(Transaction.date, Transaction.type)
        .order_by(Transaction.date)
    )

    rows = result.all()
    data: dict[str, dict] = {}
    for r in rows:
        key = str(r.date)
        if key not in data:
            data[key] = {"income": Decimal("0"), "expense": Decimal("0")}
        data[key][r.type] = r.total

    return [DailyData(date=k, income=v["income"], expense=v["expense"]) for k, v in sorted(data.items())]
