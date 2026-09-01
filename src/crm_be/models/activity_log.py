import uuid

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from crm_be.logic.calculate.calculate_datetime import get_now
from crm_be.models.base import Base
from crm_be.store.enums.activity_type import ActivityType

if TYPE_CHECKING:
    from crm_be.models.deal import Deal


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    deal_id: Mapped[str] = mapped_column(String(36), ForeignKey("deals.id"), nullable=False)
    type: Mapped[ActivityType] = mapped_column(Enum(ActivityType), nullable=False)
    activity_date: Mapped[date] = mapped_column(Date, nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=get_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=get_now, onupdate=get_now, nullable=False
    )

    deal: Mapped["Deal"] = relationship(back_populates="activity_logs")
