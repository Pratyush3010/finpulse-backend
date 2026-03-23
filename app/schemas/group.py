from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal


# ── Member ────────────────────────────────────────────────────────────────────

class GroupMemberCreate(BaseModel):
    name: str
    user_id: Optional[str] = None


class GroupMemberResponse(BaseModel):
    id: str
    name: str
    user_id: Optional[str]
    is_owner: bool

    model_config = {"from_attributes": True}


# ── Group ─────────────────────────────────────────────────────────────────────

class GroupCreate(BaseModel):
    name: str
    description: Optional[str] = None
    member_names: List[str] = []  # names of additional members (beyond creator)


class GroupResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    created_by: str
    created_at: datetime
    members: List[GroupMemberResponse] = []

    model_config = {"from_attributes": True}


class GroupSummaryResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    member_count: int
    expense_count: int
    total_amount: Decimal
    your_balance: Decimal  # positive = you are owed, negative = you owe


# ── Expense ───────────────────────────────────────────────────────────────────

class GroupExpenseSplitCreate(BaseModel):
    member_id: str
    share_amount: Decimal = Field(gt=0)


class GroupExpenseCreate(BaseModel):
    paid_by_member_id: str
    amount: Decimal = Field(gt=0)
    description: str
    category: Optional[str] = None
    date: date
    split_equally: bool = True
    custom_splits: Optional[List[GroupExpenseSplitCreate]] = None


class GroupExpenseSplitResponse(BaseModel):
    id: str
    member_id: str
    member_name: str
    share_amount: Decimal
    is_settled: bool

    model_config = {"from_attributes": True}


class GroupExpenseResponse(BaseModel):
    id: str
    group_id: str
    paid_by_member_id: str
    paid_by_name: str
    amount: Decimal
    description: str
    category: Optional[str]
    date: date
    splits: List[GroupExpenseSplitResponse] = []

    model_config = {"from_attributes": True}


# ── Balances ──────────────────────────────────────────────────────────────────

class MemberBalance(BaseModel):
    member_id: str
    member_name: str
    is_you: bool
    net_balance: Decimal  # positive = you are owed, negative = you owe


class Settlement(BaseModel):
    from_member_id: str
    from_name: str
    to_member_id: str
    to_name: str
    amount: Decimal


class GroupBalancesResponse(BaseModel):
    members: List[MemberBalance]
    settlements: List[Settlement]


# ── Settle ────────────────────────────────────────────────────────────────────

class SettleRequest(BaseModel):
    from_member_id: str
    to_member_id: str
