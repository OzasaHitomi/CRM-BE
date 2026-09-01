import os
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from crm_be.logic.security.password import hash_password
from crm_be.models.user import User
from crm_be.store.enums.account_type import AccountType


def seed_admin(db: Session) -> None:
    admin_email = os.environ.get("ADMIN_EMAIL")
    admin_password = os.environ.get("ADMIN_PASSWORD")

    if not admin_email or not admin_password:
        print("ADMIN_EMAIL or ADMIN_PASSWORD is not set. Skipping admin user creation.")
        return

    existing = db.scalar(select(User).where(User.email == admin_email))
    if existing is not None:
        print(f"Admin user '{admin_email}' already exists. Skipping.")
        return

    db.add(
        User(
            id=uuid.uuid4(),
            name="Admin User",
            email=admin_email,
            hashed_password=hash_password(admin_password),
            account_type=AccountType.admin,
            is_active=True,
        )
    )
    print(f"Admin user created: {admin_email}")
