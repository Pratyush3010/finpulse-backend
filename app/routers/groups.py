from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.models.user import User
from app.models.group import Group, GroupMember, GroupExpense, GroupExpenseSplit
from app.schemas.group import (
    GroupCreate, GroupResponse, GroupSummaryResponse,
    GroupExpenseCreate, GroupExpenseResponse, GroupExpenseSplitResponse,
    GroupBalancesResponse, MemberBalance, Settlement, SettleRequest,
    GroupMemberCreate, GroupMemberResponse,
)
from app.middleware.auth import get_current_user
from decimal import Decimal
from datetime import date as date_type
from typing import List

router = APIRouter(prefix="/groups", tags=["Groups"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _build_expense_response(expense: GroupExpense, member_map: dict) -> GroupExpenseResponse:
    splits = [
        GroupExpenseSplitResponse(
            id=s.id,
            member_id=s.member_id,
            member_name=member_map.get(s.member_id, "Unknown"),
            share_amount=s.share_amount,
            is_settled=s.is_settled,
        )
        for s in expense.splits
    ]
    return GroupExpenseResponse(
        id=expense.id,
        group_id=expense.group_id,
        paid_by_member_id=expense.paid_by_member_id,
        paid_by_name=member_map.get(expense.paid_by_member_id, "Unknown"),
        amount=expense.amount,
        description=expense.description,
        category=expense.category,
        date=expense.date,
        splits=splits,
    )


async def _get_member_map(group_id: str, db: AsyncSession) -> dict:
    result = await db.execute(select(GroupMember).where(GroupMember.group_id == group_id))
    return {m.id: m.name for m in result.scalars().all()}


async def _calc_balances(group_id: str, current_user_id: str, db: AsyncSession):
    members_result = await db.execute(select(GroupMember).where(GroupMember.group_id == group_id))
    members = members_result.scalars().all()

    expenses_result = await db.execute(
        select(GroupExpense)
        .options(selectinload(GroupExpense.splits))
        .where(GroupExpense.group_id == group_id)
    )
    expenses = expenses_result.scalars().all()

    paid = {m.id: Decimal("0") for m in members}
    owed = {m.id: Decimal("0") for m in members}

    for expense in expenses:
        paid[expense.paid_by_member_id] = paid.get(expense.paid_by_member_id, Decimal("0")) + expense.amount
        for split in expense.splits:
            if not split.is_settled:
                owed[split.member_id] = owed.get(split.member_id, Decimal("0")) + split.share_amount

    net = {mid: paid[mid] - owed[mid] for mid in paid}

    # Find which member is "you" (the current user)
    you_member_id = next((m.id for m in members if m.user_id == current_user_id), None)

    member_balances = [
        MemberBalance(
            member_id=m.id,
            member_name=m.name,
            is_you=(m.id == you_member_id),
            net_balance=net[m.id],
        )
        for m in members
    ]

    # Greedy settlement algorithm
    debtors = sorted(
        [(mid, -bal) for mid, bal in net.items() if bal < 0],
        key=lambda x: -x[1]
    )
    creditors = sorted(
        [(mid, bal) for mid, bal in net.items() if bal > 0],
        key=lambda x: -x[1]
    )
    member_map = {m.id: m.name for m in members}

    settlements: list[Settlement] = []
    i, j = 0, 0
    while i < len(debtors) and j < len(creditors):
        debtor_id, debt = debtors[i]
        creditor_id, credit = creditors[j]
        amount = min(debt, credit)
        if amount > Decimal("0.01"):
            settlements.append(Settlement(
                from_member_id=debtor_id,
                from_name=member_map[debtor_id],
                to_member_id=creditor_id,
                to_name=member_map[creditor_id],
                amount=round(amount, 2),
            ))
        debt -= amount
        credit -= amount
        debtors[i] = (debtor_id, debt)
        creditors[j] = (creditor_id, credit)
        if debt < Decimal("0.01"):
            i += 1
        if credit < Decimal("0.01"):
            j += 1

    return member_balances, settlements


# ── Groups CRUD ───────────────────────────────────────────────────────────────

@router.post("", response_model=GroupResponse, status_code=status.HTTP_201_CREATED)
async def create_group(
    data: GroupCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    group = Group(name=data.name, description=data.description, created_by=current_user.id)
    db.add(group)
    await db.flush()

    # Add creator as first member (owner)
    owner = GroupMember(group_id=group.id, user_id=current_user.id, name=current_user.name, is_owner=True)
    db.add(owner)

    # Add extra members by name
    for name in data.member_names:
        if name.strip():
            db.add(GroupMember(group_id=group.id, name=name.strip(), is_owner=False))

    await db.commit()

    result = await db.execute(
        select(Group).options(selectinload(Group.members)).where(Group.id == group.id)
    )
    return result.scalar_one()


@router.get("", response_model=List[GroupSummaryResponse])
async def list_groups(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Group)
        .options(selectinload(Group.members), selectinload(Group.expenses).selectinload(GroupExpense.splits))
        .where(Group.created_by == current_user.id)
        .order_by(Group.created_at.desc())
    )
    groups = result.scalars().all()

    summaries = []
    for group in groups:
        total = sum(e.amount for e in group.expenses)
        # Find the member representing current user
        you = next((m for m in group.members if m.user_id == current_user.id), None)
        your_balance = Decimal("0")
        if you:
            paid = sum(e.amount for e in group.expenses if e.paid_by_member_id == you.id)
            owed = sum(
                s.share_amount
                for e in group.expenses
                for s in e.splits
                if s.member_id == you.id and not s.is_settled
            )
            your_balance = paid - owed

        summaries.append(GroupSummaryResponse(
            id=group.id,
            name=group.name,
            description=group.description,
            member_count=len(group.members),
            expense_count=len(group.expenses),
            total_amount=total,
            your_balance=your_balance,
        ))
    return summaries


@router.get("/{group_id}", response_model=GroupResponse)
async def get_group(
    group_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Group)
        .options(selectinload(Group.members))
        .where(Group.id == group_id, Group.created_by == current_user.id)
    )
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    return group


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_group(
    group_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Group).where(Group.id == group_id, Group.created_by == current_user.id)
    )
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    await db.delete(group)
    await db.commit()


# ── Members ───────────────────────────────────────────────────────────────────

@router.post("/{group_id}/members", response_model=GroupMemberResponse, status_code=status.HTTP_201_CREATED)
async def add_member(
    group_id: str,
    data: GroupMemberCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Group).where(Group.id == group_id, Group.created_by == current_user.id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Group not found")

    member = GroupMember(group_id=group_id, name=data.name, user_id=data.user_id, is_owner=False)
    db.add(member)
    await db.commit()
    await db.refresh(member)
    return member


@router.delete("/{group_id}/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    group_id: str,
    member_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Group).where(Group.id == group_id, Group.created_by == current_user.id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Group not found")

    member_result = await db.execute(
        select(GroupMember).where(GroupMember.id == member_id, GroupMember.group_id == group_id)
    )
    member = member_result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    if member.is_owner:
        raise HTTPException(status_code=400, detail="Cannot remove the group owner")

    await db.delete(member)
    await db.commit()


# ── Expenses ──────────────────────────────────────────────────────────────────

@router.get("/{group_id}/expenses", response_model=List[GroupExpenseResponse])
async def list_expenses(
    group_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Group).where(Group.id == group_id, Group.created_by == current_user.id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Group not found")

    expenses_result = await db.execute(
        select(GroupExpense)
        .options(selectinload(GroupExpense.splits))
        .where(GroupExpense.group_id == group_id)
        .order_by(GroupExpense.date.desc(), GroupExpense.created_at.desc())
    )
    expenses = expenses_result.scalars().all()
    member_map = await _get_member_map(group_id, db)
    return [_build_expense_response(e, member_map) for e in expenses]


@router.post("/{group_id}/expenses", response_model=GroupExpenseResponse, status_code=status.HTTP_201_CREATED)
async def add_expense(
    group_id: str,
    data: GroupExpenseCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Group).where(Group.id == group_id, Group.created_by == current_user.id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Group not found")

    # Validate payer is in this group
    payer_result = await db.execute(
        select(GroupMember).where(
            GroupMember.id == data.paid_by_member_id,
            GroupMember.group_id == group_id
        )
    )
    if not payer_result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Payer is not a member of this group")

    # Get all members for splitting
    members_result = await db.execute(select(GroupMember).where(GroupMember.group_id == group_id))
    members = members_result.scalars().all()

    expense = GroupExpense(
        group_id=group_id,
        paid_by_member_id=data.paid_by_member_id,
        amount=data.amount,
        description=data.description,
        category=data.category,
        date=data.date,
    )
    db.add(expense)
    await db.flush()

    if data.split_equally:
        share = round(data.amount / len(members), 2)
        # Correct rounding: give remainder to first member
        remainder = data.amount - share * len(members)
        for i, member in enumerate(members):
            member_share = share + (remainder if i == 0 else Decimal("0"))
            db.add(GroupExpenseSplit(
                expense_id=expense.id,
                member_id=member.id,
                share_amount=member_share,
                is_settled=(member.id == data.paid_by_member_id),  # payer's own share auto-settled
            ))
    else:
        if not data.custom_splits:
            raise HTTPException(status_code=400, detail="custom_splits required when split_equally=false")
        total_custom = sum(s.share_amount for s in data.custom_splits)
        if abs(total_custom - data.amount) > Decimal("0.02"):
            raise HTTPException(status_code=400, detail="Custom splits must sum to expense amount")
        for s in data.custom_splits:
            db.add(GroupExpenseSplit(
                expense_id=expense.id,
                member_id=s.member_id,
                share_amount=s.share_amount,
                is_settled=(s.member_id == data.paid_by_member_id),
            ))

    await db.commit()

    exp_result = await db.execute(
        select(GroupExpense).options(selectinload(GroupExpense.splits)).where(GroupExpense.id == expense.id)
    )
    saved = exp_result.scalar_one()
    member_map = await _get_member_map(group_id, db)
    return _build_expense_response(saved, member_map)


@router.delete("/{group_id}/expenses/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_expense(
    group_id: str,
    expense_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Group).where(Group.id == group_id, Group.created_by == current_user.id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Group not found")

    exp_result = await db.execute(
        select(GroupExpense).where(GroupExpense.id == expense_id, GroupExpense.group_id == group_id)
    )
    expense = exp_result.scalar_one_or_none()
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")

    await db.delete(expense)
    await db.commit()


# ── Balances ──────────────────────────────────────────────────────────────────

@router.get("/{group_id}/balances", response_model=GroupBalancesResponse)
async def get_balances(
    group_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Group).where(Group.id == group_id, Group.created_by == current_user.id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Group not found")

    member_balances, settlements = await _calc_balances(group_id, current_user.id, db)
    return GroupBalancesResponse(members=member_balances, settlements=settlements)


# ── Settle ────────────────────────────────────────────────────────────────────

@router.post("/{group_id}/settle", status_code=status.HTTP_200_OK)
async def settle_up(
    group_id: str,
    data: SettleRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark all unsettled splits where from_member owes to_member as settled."""
    result = await db.execute(
        select(Group).where(Group.id == group_id, Group.created_by == current_user.id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Group not found")

    # Get all expenses paid by to_member
    expenses_result = await db.execute(
        select(GroupExpense.id).where(
            GroupExpense.group_id == group_id,
            GroupExpense.paid_by_member_id == data.to_member_id,
        )
    )
    expense_ids = [row[0] for row in expenses_result.all()]

    if not expense_ids:
        return {"settled": 0}

    # Mark from_member's splits in those expenses as settled
    splits_result = await db.execute(
        select(GroupExpenseSplit).where(
            GroupExpenseSplit.expense_id.in_(expense_ids),
            GroupExpenseSplit.member_id == data.from_member_id,
            GroupExpenseSplit.is_settled == False,  # noqa
        )
    )
    splits = splits_result.scalars().all()
    for s in splits:
        s.is_settled = True

    await db.commit()
    return {"settled": len(splits)}
