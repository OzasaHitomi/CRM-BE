import uuid

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from crm_be.logic.calculate.calculate_datetime import get_now
from crm_be.models.base import Base
from crm_be.store.enums.deal_plan import DealPlan
from crm_be.store.enums.deal_status import DealStatus

if TYPE_CHECKING:
    from crm_be.models.activity_log import ActivityLog
    from crm_be.models.customer import Customer


class Deal(Base):
    __tablename__ = "deals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_id: Mapped[str] = mapped_column(String(36), ForeignKey("customers.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[DealStatus] = mapped_column(Enum(DealStatus), nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    plan: Mapped[DealPlan] = mapped_column(Enum(DealPlan), nullable=False)
    license_count: Mapped[int] = mapped_column(Integer, nullable=False)
    contract_period: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=get_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=get_now, onupdate=get_now, nullable=False
    )

    customer: Mapped["Customer"] = relationship(back_populates="deals")
    activity_logs: Mapped[list["ActivityLog"]] = relationship(
        back_populates="deal", order_by="ActivityLog.created_at.desc()"
    )
