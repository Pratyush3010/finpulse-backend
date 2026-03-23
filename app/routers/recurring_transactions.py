from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.models.user import User
from app.models.category import Category
from app.models.transaction import Transaction
from app.models.recurring_transaction import RecurringTransaction
from app.schemas.recurring_transaction import (
    RecurringTransactionCreate,
    RecurringTransactionUpdate,
    RecurringTransactionResponse,
)
from app.middleware.auth import get_current_user
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta

router = APIRouter(prefix="/recurring-transactions", tags=["Recurring Transactions"])


def _next_occurrence(frequency: str, from_date: date) -> date:
    if frequency == "daily":
        return from_date + timedelta(days=1)
    elif frequency == "weekly":
        return from_date + timedelta(weeks=1)
    elif frequency == "monthly":
        return from_date + relativedelta(months=1)
    elif frequency == "yearly":
        return from_date + relativedelta(years=1)
    return from_date


@router.get("", response_model=list[RecurringTransactionResponse])
async def get_recurring_transactions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(RecurringTransaction)
        .options(selectinload(RecurringTransaction.category))
        .where(RecurringTransaction.user_id == current_user.id)
        .order_by(RecurringTransaction.next_date)
    )
    return result.scalars().all()


@router.post("", response_model=RecurringTransactionResponse, status_code=status.HTTP_201_CREATED)
async def create_recurring_transaction(
    data: RecurringTransactionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    cat_result = await db.execute(
        select(Category).where(Category.id == data.category_id, Category.user_id == current_user.id)
    )
    if not cat_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Category not found")

    rt = RecurringTransaction(
        user_id=current_user.id,
        next_date=data.start_date,
        **data.model_dump(),
    )
    db.add(rt)
    await db.commit()

    result = await db.execute(
        select(RecurringTransaction)
        .options(selectinload(RecurringTransaction.category))
        .where(RecurringTransaction.id == rt.id)
    )
    return result.scalar_one()


@router.put("/{rt_id}", response_model=RecurringTransactionResponse)
async def update_recurring_transaction(
    rt_id: str,
    data: RecurringTransactionUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(RecurringTransaction).where(
            RecurringTransaction.id == rt_id,
            RecurringTransaction.user_id == current_user.id,
        )
    )
    rt = result.scalar_one_or_none()
    if not rt:
        raise HTTPException(status_code=404, detail="Recurring transaction not found")

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(rt, field, value)

    await db.commit()

    result = await db.execute(
        select(RecurringTransaction)
        .options(selectinload(RecurringTransaction.category))
        .where(RecurringTransaction.id == rt.id)
    )
    return result.scalar_one()


@router.delete("/{rt_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_recurring_transaction(
    rt_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(RecurringTransaction).where(
            RecurringTransaction.id == rt_id,
            RecurringTransaction.user_id == current_user.id,
        )
    )
    rt = result.scalar_one_or_none()
    if not rt:
        raise HTTPException(status_code=404, detail="Recurring transaction not found")
    await db.delete(rt)
    await db.commit()


@router.post("/{rt_id}/generate", response_model=list[dict])
async def generate_pending(
    rt_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate all pending transaction entries up to today for a recurring rule."""
    result = await db.execute(
        select(RecurringTransaction).where(
            RecurringTransaction.id == rt_id,
            RecurringTransaction.user_id == current_user.id,
        )
    )
    rt = result.scalar_one_or_none()
    if not rt:
        raise HTTPException(status_code=404, detail="Recurring transaction not found")
    if not rt.is_active:
        raise HTTPException(status_code=400, detail="Recurring transaction is not active")

    today = date.today()
    generated = []
    next_d = rt.next_date or rt.start_date

    while next_d <= today:
        if rt.end_date and next_d > rt.end_date:
            break
        t = Transaction(
            user_id=current_user.id,
            category_id=rt.category_id,
            amount=rt.amount,
            type=rt.type,
            description=rt.description,
            date=next_d,
        )
        db.add(t)
        generated.append({"date": str(next_d), "amount": str(rt.amount)})
        next_d = _next_occurrence(rt.frequency, next_d)

    rt.next_date = next_d
    await db.commit()
    return generated
