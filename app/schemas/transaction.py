from pydantic import BaseModel
from datetime import datetime, date
from decimal import Decimal
from typing import Optional
from app.schemas.category import CategoryResponse


class TransactionCreate(BaseModel):
    category_id: str
    amount: Decimal
    type: str  # "income" | "expense"
    description: Optional[str] = None
    date: date


class TransactionUpdate(BaseModel):
    category_id: Optional[str] = None
    amount: Optional[Decimal] = None
    type: Optional[str] = None
    description: Optional[str] = None
    date: Optional[date] = None


class TransactionResponse(BaseModel):
    id: str
    user_id: str
    category_id: str
    amount: Decimal
    type: str
    description: Optional[str]
    date: date
    created_at: datetime
    category: Optional[CategoryResponse] = None

    model_config = {"from_attributes": True}


class TransactionListResponse(BaseModel):
    transactions: list[TransactionResponse]
    total: int
    page: int
    per_page: int
