import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from crm_be.models.user import User
from crm_be.store.enums.account_type import AccountType


def get_user_by_id(session: Session, user_id: uuid.UUID) -> User | None:
    return session.scalars(select(User).where(User.id == str(user_id))).first()


def get_user_by_email(session: Session, email: str) -> User | None:
    return session.scalars(select(User).where(User.email == email)).first()


def get_users_by_account_types(session: Session, account_types: list[AccountType]) -> list[User]:
    stmt = select(User).where(User.account_type.in_(account_types)).order_by(User.created_at.desc())
    return list(session.scalars(stmt))


def create_user(session: Session, user: User) -> User:
    session.add(user)
    try:
        session.commit()
    except Exception:
        session.rollback()
        raise
    session.refresh(user)
    return user


def update_user_status(session: Session, user: User, is_active: bool) -> User:
    user.is_active = is_active
    try:
        session.commit()
    except Exception:
        session.rollback()
        raise
    session.refresh(user)
    return user
