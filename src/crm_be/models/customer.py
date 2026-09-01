import uuid

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from crm_be.logic.calculate.calculate_datetime import get_now
from crm_be.models.base import Base
from crm_be.store.enums.industry_type import IndustryType

if TYPE_CHECKING:
    from crm_be.models.deal import Deal
    from crm_be.models.user import User


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    company_name: Mapped[str] = mapped_column(String(100), nullable=False)
    industry: Mapped[IndustryType] = mapped_column(Enum(IndustryType), nullable=False)
    company_size: Mapped[int] = mapped_column(Integer, nullable=False)
    contact_name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    assigned_user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=get_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=get_now, onupdate=get_now, nullable=False
    )

    assigned_user: Mapped["User | None"] = relationship(back_populates="customers")
    deals: Mapped[list["Deal"]] = relationship(
        back_populates="customer", order_by="Deal.created_at.desc()"
    )
