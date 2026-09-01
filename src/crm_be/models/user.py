import uuid

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from crm_be.logic.calculate.calculate_datetime import get_now
from crm_be.models.base import Base
from crm_be.store.enums.account_type import AccountType

if TYPE_CHECKING:
    from crm_be.models.customer import Customer


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    account_type: Mapped[AccountType] = mapped_column(Enum(AccountType), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=get_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=get_now, onupdate=get_now, nullable=False
    )

    customers: Mapped[list["Customer"]] = relationship(back_populates="assigned_user")
