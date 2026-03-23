from pydantic import BaseModel, Field
from typing import Optional
from datetime import date
from decimal import Decimal


class SavingsGoalCreate(BaseModel):
    name: str
    target_amount: Decimal = Field(gt=0)
    target_date: Optional[date] = None
    icon: Optional[str] = "savings"
    color: Optional[str] = "#6C63FF"


class SavingsGoalUpdate(BaseModel):
    name: Optional[str] = None
    target_amount: Optional[Decimal] = Field(default=None, gt=0)
    target_date: Optional[date] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    is_completed: Optional[bool] = None


class SavingsGoalDepositRequest(BaseModel):
    amount: Decimal = Field(gt=0)


class SavingsGoalResponse(BaseModel):
    id: str
    name: str
    target_amount: Decimal
    saved_amount: Decimal
    target_date: Optional[date]
    icon: str
    color: str
    is_completed: bool

    model_config = {"from_attributes": True}
