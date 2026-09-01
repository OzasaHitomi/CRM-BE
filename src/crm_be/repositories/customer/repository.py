from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from crm_be.models.customer import Customer
from crm_be.models.deal import Deal
from crm_be.store.enums.industry_type import IndustryType


def create_customer(session: Session, customer: Customer) -> Customer:
    session.add(customer)
    try:
        session.commit()
    except Exception:
        session.rollback()
        raise
    session.refresh(customer)
    return customer


def get_customers(session: Session, visible_to_user_id: str | None = None) -> list[Customer]:
    stmt = select(Customer).options(joinedload(Customer.assigned_user))
    if visible_to_user_id is not None:
        stmt = stmt.where(
            or_(
                Customer.assigned_user_id == visible_to_user_id,
                Customer.assigned_user_id.is_(None),
            )
        )
    stmt = stmt.order_by(Customer.created_at.desc())
    return list(session.scalars(stmt))


def get_customer_by_id(
    session: Session, customer_id: str, *, for_update: bool = False
) -> Customer | None:
    stmt = (
        select(Customer)
        .options(
            joinedload(Customer.assigned_user),
            selectinload(Customer.deals).selectinload(Deal.activity_logs),
        )
        .where(Customer.id == customer_id)
    )
    if for_update:
        stmt = stmt.with_for_update()
    return session.scalars(stmt).one_or_none()


def assign_customer_user(session: Session, customer: Customer, user_id: str) -> Customer:
    customer.assigned_user_id = user_id
    try:
        session.commit()
    except Exception:
        session.rollback()
        raise
    session.refresh(customer)
    return customer


def unassign_customer_user(session: Session, customer: Customer) -> Customer:
    customer.assigned_user_id = None
    try:
        session.commit()
    except Exception:
        session.rollback()
        raise
    session.refresh(customer)
    return customer


def update_customer(
    session: Session,
    customer: Customer,
    company_name: str,
    industry: IndustryType,
    company_size: int,
    contact_name: str,
    phone: str,
    email: str,
) -> Customer:
    customer.company_name = company_name
    customer.industry = industry
    customer.company_size = company_size
    customer.contact_name = contact_name
    customer.phone = phone
    customer.email = email
    try:
        session.commit()
    except Exception:
        session.rollback()
        raise
    session.refresh(customer)
    return customer
