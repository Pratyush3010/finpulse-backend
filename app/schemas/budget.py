from pydantic import BaseModel
from datetime import datetime, date
from decimal import Decimal
from typing import Optional
from app.schemas.category import CategoryResponse


class BudgetCreate(BaseModel):
    name: str
    category_id: Optional[str] = None
    amount: Decimal
    period: str = "monthly"  # "weekly" | "monthly" | "yearly"
    start_date: date
    end_date: Optional[date] = None


class BudgetUpdate(BaseModel):
    name: Optional[str] = None
    amount: Optional[Decimal] = None
    period: Optional[str] = None
    end_date: Optional[date] = None


class BudgetResponse(BaseModel):
    id: str
    user_id: str
    category_id: Optional[str]
    name: str
    amount: Decimal
    period: str
    start_date: date
    end_date: Optional[date]
    created_at: datetime
    category: Optional[CategoryResponse] = None
    spent: Optional[Decimal] = None
    remaining: Optional[Decimal] = None
    percentage: Optional[float] = None

    model_config = {"from_attributes": True}
