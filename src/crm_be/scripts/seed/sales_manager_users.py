import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from crm_be.logic.security.password import hash_password
from crm_be.models.user import User
from crm_be.store.enums.account_type import AccountType

HASHED_PASSWORD = hash_password("password")


def seed_sales_manager_users(db: Session) -> tuple[User, User] | None:
    """sales@example.com / manager@example.com を作成する。
    既に存在する場合は何もせずNoneを返す。
    """
    existing = db.scalar(select(User).where(User.email == "sales@example.com"))
    if existing is not None:
        return None

    sales_user = User(
        id=str(uuid.uuid4()),
        name="営業 太郎",
        email="sales@example.com",
        hashed_password=HASHED_PASSWORD,
        account_type=AccountType.sales,
        is_active=True,
    )
    manager_user = User(
        id=str(uuid.uuid4()),
        name="営業 花子",
        email="manager@example.com",
        hashed_password=HASHED_PASSWORD,
        account_type=AccountType.manager,
        is_active=True,
    )
    db.add_all([sales_user, manager_user])
    db.flush()

    return sales_user, manager_user
