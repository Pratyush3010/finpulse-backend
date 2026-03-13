from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.models.user import User
from app.models.budget import Budget
from app.models.transaction import Transaction
from app.schemas.budget import BudgetCreate, BudgetUpdate, BudgetResponse
from app.middleware.auth import get_current_user
from datetime import date
from decimal import Decimal

router = APIRouter(prefix="/budgets", tags=["Budgets"])


async def _enrich_budget(budget: Budget, db: AsyncSession) -> BudgetResponse:
    today = date.today()
    query = select(func.sum(Transaction.amount)).where(
        Transaction.user_id == budget.user_id,
        Transaction.type == "expense",
        Transaction.date >= budget.start_date,
    )
    if budget.end_date:
        query = query.where(Transaction.date <= budget.end_date)
    else:
        query = query.where(Transaction.date <= today)

    if budget.category_id:
        query = query.where(Transaction.category_id == budget.category_id)

    result = await db.execute(query)
    spent = result.scalar() or Decimal("0")
    remaining = budget.amount - spent
    percentage = float(spent / budget.amount * 100) if budget.amount > 0 else 0.0

    resp = BudgetResponse.model_validate(budget)
    resp.spent = spent
    resp.remaining = remaining
    resp.percentage = round(percentage, 2)
    return resp


@router.get("", response_model=list[BudgetResponse])
async def get_budgets(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Budget).options(selectinload(Budget.category)).where(Budget.user_id == current_user.id)
    )
    budgets = result.scalars().all()
    return [await _enrich_budget(b, db) for b in budgets]


@router.post("", response_model=BudgetResponse, status_code=status.HTTP_201_CREATED)
async def create_budget(
    data: BudgetCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    budget = Budget(user_id=current_user.id, **data.model_dump())
    db.add(budget)
    await db.commit()

    result = await db.execute(
        select(Budget).options(selectinload(Budget.category)).where(Budget.id == budget.id)
    )
    return await _enrich_budget(result.scalar_one(), db)


@router.put("/{budget_id}", response_model=BudgetResponse)
async def update_budget(
    budget_id: str,
    data: BudgetUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Budget).where(Budget.id == budget_id, Budget.user_id == current_user.id)
    )
    budget = result.scalar_one_or_none()
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(budget, field, value)

    await db.commit()

    result = await db.execute(
        select(Budget).options(selectinload(Budget.category)).where(Budget.id == budget.id)
    )
    return await _enrich_budget(result.scalar_one(), db)


@router.delete("/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_budget(
    budget_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Budget).where(Budget.id == budget_id, Budget.user_id == current_user.id)
    )
    budget = result.scalar_one_or_none()
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")
    await db.delete(budget)
    await db.commit()
