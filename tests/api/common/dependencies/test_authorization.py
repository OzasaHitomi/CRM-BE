import pytest

from fastapi import HTTPException

from crm_be.api.common.dependencies.authorization import user_checker
from crm_be.models.user import User
from crm_be.store.enums.account_type import AccountType


def build_user(account_type: AccountType) -> User:
    return User(
        id="user-id",
        name="テストユーザー",
        email="checker@example.com",
        hashed_password="hashed",
        account_type=account_type,
    )


class TestUserChecker:
    def test_allows_user_with_permitted_role(self) -> None:
        checker = user_checker({AccountType.admin})
        user = build_user(AccountType.admin)

        checker(user)

    def test_raises_when_role_is_not_permitted(self) -> None:
        checker = user_checker({AccountType.admin})
        user = build_user(AccountType.sales)

        with pytest.raises(HTTPException) as exc_info:
            checker(user)

        assert exc_info.value.status_code == 403

    def test_allows_role_matching_any_of_multiple_permitted_roles(self) -> None:
        checker = user_checker({AccountType.admin, AccountType.manager})
        user = build_user(AccountType.manager)

        checker(user)
