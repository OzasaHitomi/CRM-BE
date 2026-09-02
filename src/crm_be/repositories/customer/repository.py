from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from crm_be.models.customer import Customer
from crm_be.models.deal import Deal
from crm_be.store.enums.industry_type import IndustryType

# 顧客一覧の1ページあたりの件数。可変にする要件がないため固定値としている。
PAGE_SIZE = 10


def create_customer(session: Session, customer: Customer) -> Customer:
    session.add(customer)
    try:
        session.commit()
    except Exception:
        session.rollback()
        raise
    session.refresh(customer)
    return customer


def get_customers(
    session: Session,
    visible_to_user_id: str | None = None,
    *,
    page: int = 1,
) -> tuple[list[Customer], int]:
    # 「絞り込み条件（visible_to_user_id）」だけを持つベースのクエリを先に作る。
    # ここにLIMIT/OFFSETを付けず、件数カウントと実データ取得の両方で使い回す。
    base_stmt = select(Customer)
    if visible_to_user_id is not None:
        base_stmt = base_stmt.where(
            or_(
                Customer.assigned_user_id == visible_to_user_id,
                Customer.assigned_user_id.is_(None),
            )
        )

    # ページ分割する前の「絞り込み後の全件数」を取得する。
    # FEが総ページ数を計算したり、「◯件中△件」のような表示をするために必要。
    total_count = session.scalar(select(func.count()).select_from(base_stmt.subquery())) or 0

    # 実際にそのページ分だけデータを取得するクエリ。
    # limit: 1ページあたりの件数、offset: 先頭から何件飛ばすか。
    # 例）page=2 のとき offset=10 → 11件目から10件を取得する。
    stmt = (
        base_stmt.options(joinedload(Customer.assigned_user))
        .order_by(Customer.created_at.desc())
        .limit(PAGE_SIZE)
        .offset((page - 1) * PAGE_SIZE)
    )
    customers = list(session.scalars(stmt))

    return customers, total_count


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
