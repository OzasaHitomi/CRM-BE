from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from crm_be.models.activity_log import ActivityLog
from crm_be.models.deal import Deal
from crm_be.store.enums.activity_type import ActivityType


def create_activity_log(session: Session, activity_log: ActivityLog) -> ActivityLog:
    session.add(activity_log)
    try:
        session.commit()
    except Exception:
        session.rollback()
        raise
    session.refresh(activity_log)
    return activity_log


def get_activity_log_by_id(session: Session, activity_log_id: str) -> ActivityLog | None:
    stmt = (
        select(ActivityLog)
        .options(joinedload(ActivityLog.deal).joinedload(Deal.customer))
        .where(ActivityLog.id == activity_log_id)
    )
    return session.scalars(stmt).one_or_none()


def update_activity_log(
    session: Session,
    activity_log: ActivityLog,
    type: ActivityType,
    activity_date: date,
    note: str | None,
) -> ActivityLog:
    activity_log.type = type
    activity_log.activity_date = activity_date
    activity_log.note = note
    try:
        session.commit()
    except Exception:
        session.rollback()
        raise
    session.refresh(activity_log)
    return activity_log
