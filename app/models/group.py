from sqlalchemy import String, ForeignKey, DateTime, Numeric, func, Date, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from decimal import Decimal
import uuid


class Group(Base):
    __tablename__ = "groups"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=True)
    created_by: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    members: Mapped[list["GroupMember"]] = relationship(
        "GroupMember", back_populates="group", cascade="all, delete-orphan"
    )
    expenses: Mapped[list["GroupExpense"]] = relationship(
        "GroupExpense", back_populates="group", cascade="all, delete-orphan"
    )


class GroupMember(Base):
    __tablename__ = "group_members"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    group_id: Mapped[str] = mapped_column(String, ForeignKey("groups.id"), nullable=False)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=True)  # null for non-app users
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_owner: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    group: Mapped["Group"] = relationship("Group", back_populates="members")
    splits: Mapped[list["GroupExpenseSplit"]] = relationship(
        "GroupExpenseSplit", back_populates="member", cascade="all, delete-orphan",
        foreign_keys="GroupExpenseSplit.member_id"
    )
    paid_expenses: Mapped[list["GroupExpense"]] = relationship(
        "GroupExpense", back_populates="paid_by_member"
    )


class GroupExpense(Base):
    __tablename__ = "group_expenses"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    group_id: Mapped[str] = mapped_column(String, ForeignKey("groups.id"), nullable=False)
    paid_by_member_id: Mapped[str] = mapped_column(String, ForeignKey("group_members.id"), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=True)
    date: Mapped[Date] = mapped_column(Date, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    group: Mapped["Group"] = relationship("Group", back_populates="expenses")
    paid_by_member: Mapped["GroupMember"] = relationship("GroupMember", back_populates="paid_expenses")
    splits: Mapped[list["GroupExpenseSplit"]] = relationship(
        "GroupExpenseSplit", back_populates="expense", cascade="all, delete-orphan"
    )


class GroupExpenseSplit(Base):
    __tablename__ = "group_expense_splits"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    expense_id: Mapped[str] = mapped_column(String, ForeignKey("group_expenses.id"), nullable=False)
    member_id: Mapped[str] = mapped_column(String, ForeignKey("group_members.id"), nullable=False)
    share_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    is_settled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    expense: Mapped["GroupExpense"] = relationship("GroupExpense", back_populates="splits")
    member: Mapped["GroupMember"] = relationship(
        "GroupMember", back_populates="splits", foreign_keys=[member_id]
    )
