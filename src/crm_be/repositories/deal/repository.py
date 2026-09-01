from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from crm_be.models.deal import Deal
from crm_be.store.enums.deal_plan import DealPlan
from crm_be.store.enums.deal_status import DealStatus


def create_deal(session: Session, deal: Deal) -> Deal:
    session.add(deal)
    try:
        session.commit()
    except Exception:
        session.rollback()
        raise
    session.refresh(deal)
    return deal


def get_deal_by_id(session: Session, deal_id: str, *, for_update: bool = False) -> Deal | None:
    stmt = select(Deal).options(joinedload(Deal.customer)).where(Deal.id == deal_id)
    if for_update:
        stmt = stmt.with_for_update()
    return session.scalars(stmt).one_or_none()


def update_deal(
    session: Session,
    deal: Deal,
    title: str,
    amount: int,
    plan: DealPlan,
    license_count: int,
    contract_period: int,
) -> Deal:
    deal.title = title
    deal.amount = amount
    deal.plan = plan
    deal.license_count = license_count
    deal.contract_period = contract_period
    try:
        session.commit()
    except Exception:
        session.rollback()
        raise
    session.refresh(deal)
    return deal


def update_deal_status(session: Session, deal: Deal, status: DealStatus) -> Deal:
    deal.status = status
    try:
        session.commit()
    except Exception:
        session.rollback()
        raise
    session.refresh(deal)
    return deal
