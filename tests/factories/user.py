import uuid

from sqlalchemy.orm import Session

from crm_be.logic.security.password import hash_password
from crm_be.models.user import User
from crm_be.store.enums.account_type import AccountType


def create_user(db: Session, **override: object) -> User:
    defaults: dict[str, object] = {
        "id": str(uuid.uuid4()),
        "name": "テストユーザー",
        "email": f"test_{uuid.uuid4().hex[:8]}@example.com",
        "hashed_password": hash_password("password"),
        "account_type": AccountType.sales,
        "is_active": True,
    }
    defaults.update(override)
    user = User(**defaults)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
