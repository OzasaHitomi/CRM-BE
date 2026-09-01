from collections.abc import Callable

from fastapi import Depends

from crm_be.api.common.dependencies.authentication import get_current_user
from crm_be.exceptions.forbidden_exception import ForbiddenException
from crm_be.models.user import User
from crm_be.store.enums.account_type import AccountType


def user_checker(roles: set[AccountType]) -> Callable[[User], None]:
    def checker(current_user: User = Depends(get_current_user)) -> None:
        if current_user.account_type not in roles:
            raise ForbiddenException("ユーザーの役割が不正です")

    return checker
