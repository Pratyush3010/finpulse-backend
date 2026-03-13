from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class CategoryCreate(BaseModel):
    name: str
    icon: str = "category"
    color: str = "#6C63FF"
    type: str  # "income" | "expense"


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None


class CategoryResponse(BaseModel):
    id: str
    user_id: str
    name: str
    icon: str
    color: str
    type: str
    created_at: datetime

    model_config = {"from_attributes": True}
