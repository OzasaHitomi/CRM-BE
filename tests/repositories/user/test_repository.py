import uuid

from datetime import UTC, datetime, timedelta

import pytest

from sqlalchemy.orm import Session

from crm_be.models.user import User
from crm_be.repositories.user.repository import (
    create_user,
    get_users_by_account_types,
    update_user_status,
)
from crm_be.store.enums.account_type import AccountType
from tests.conftest import RollbackTracker


def build_user(**override: object) -> User:
    defaults: dict[str, object] = {
        "id": str(uuid.uuid4()),
        "name": "テストユーザー",
        "email": f"test_{uuid.uuid4().hex[:8]}@example.com",
        "hashed_password": "hashed",
        "account_type": AccountType.sales,
    }
    defaults.update(override)
    return User(**defaults)


class TestCreateUser:
    def test_persists_user(self, db_session: Session) -> None:
        user = build_user()

        created_user = create_user(db_session, user)

        db_session.expire_all()
        assert db_session.get(User, created_user.id) is not None

    def test_returns_persisted_user(self, db_session: Session) -> None:
        user = build_user(name="山田太郎")

        created_user = create_user(db_session, user)

        assert created_user.name == "山田太郎"

    def test_rolls_back_on_commit_failure(
        self, db_session_commit_error: Session, rollback_tracker: RollbackTracker
    ) -> None:
        user = build_user()

        with pytest.raises(Exception, match="Simulated commit error"):
            create_user(db_session_commit_error, user)

        assert rollback_tracker.called is True


class TestGetUsersByAccountTypes:
    def test_returns_only_matching_account_types(self, db_session: Session) -> None:
        sales_user = create_user(db_session, build_user(account_type=AccountType.sales))
        create_user(db_session, build_user(account_type=AccountType.admin))

        result = get_users_by_account_types(db_session, [AccountType.sales])

        assert [user.id for user in result] == [sales_user.id]

    def test_returns_users_matching_any_of_multiple_account_types(
        self, db_session: Session
    ) -> None:
        sales_user = create_user(db_session, build_user(account_type=AccountType.sales))
        manager_user = create_user(db_session, build_user(account_type=AccountType.manager))
        create_user(db_session, build_user(account_type=AccountType.admin))

        result = get_users_by_account_types(db_session, [AccountType.sales, AccountType.manager])

        assert {user.id for user in result} == {sales_user.id, manager_user.id}

    def test_returns_empty_list_when_no_account_type_matches(self, db_session: Session) -> None:
        create_user(db_session, build_user(account_type=AccountType.sales))

        result = get_users_by_account_types(db_session, [AccountType.admin])

        assert result == []

    def test_orders_by_created_at_descending(self, db_session: Session) -> None:
        now = datetime.now(UTC)
        older_user = create_user(db_session, build_user(created_at=now - timedelta(days=1)))
        newer_user = create_user(db_session, build_user(created_at=now))

        result = get_users_by_account_types(db_session, [AccountType.sales])

        assert [user.id for user in result] == [newer_user.id, older_user.id]


class TestUpdateUserStatus:
    def test_deactivates_user(self, db_session: Session) -> None:
        user = create_user(db_session, build_user(is_active=True))

        update_user_status(db_session, user, False)

        db_session.expire_all()
        persisted_user = db_session.get(User, user.id)
        assert persisted_user is not None
        assert persisted_user.is_active is False

    def test_activates_user(self, db_session: Session) -> None:
        user = create_user(db_session, build_user(is_active=False))

        update_user_status(db_session, user, True)

        db_session.expire_all()
        persisted_user = db_session.get(User, user.id)
        assert persisted_user is not None
        assert persisted_user.is_active is True

    def test_returns_updated_user(self, db_session: Session) -> None:
        user = create_user(db_session, build_user(is_active=True))

        updated_user = update_user_status(db_session, user, False)

        assert updated_user.is_active is False

    def test_rolls_back_on_commit_failure(
        self,
        db_session: Session,
        db_session_commit_error: Session,
        rollback_tracker: RollbackTracker,
    ) -> None:
        user = create_user(db_session, build_user(is_active=True))

        with pytest.raises(Exception, match="Simulated commit error"):
            update_user_status(db_session_commit_error, user, False)

        assert rollback_tracker.called is True

        db_session.expire_all()
        persisted_user = db_session.get(User, user.id)
        assert persisted_user is not None
        assert persisted_user.is_active is True
