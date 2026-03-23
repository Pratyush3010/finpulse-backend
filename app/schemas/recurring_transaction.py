from pydantic import BaseModel, Field
from typing import Optional
from datetime import date
from decimal import Decimal
from app.schemas.category import CategoryResponse


class RecurringTransactionCreate(BaseModel):
    category_id: str
    amount: Decimal = Field(gt=0)
    type: str  # "income" | "expense"
    description: Optional[str] = None
    frequency: str  # "daily" | "weekly" | "monthly" | "yearly"
    start_date: date
    end_date: Optional[date] = None


class RecurringTransactionUpdate(BaseModel):
    category_id: Optional[str] = None
    amount: Optional[Decimal] = Field(default=None, gt=0)
    description: Optional[str] = None
    frequency: Optional[str] = None
    end_date: Optional[date] = None
    is_active: Optional[bool] = None


class RecurringTransactionResponse(BaseModel):
    id: str
    category_id: str
    amount: Decimal
    type: str
    description: Optional[str]
    frequency: str
    start_date: date
    end_date: Optional[date]
    next_date: Optional[date]
    is_active: bool
    category: Optional[CategoryResponse] = None

    model_config = {"from_attributes": True}
