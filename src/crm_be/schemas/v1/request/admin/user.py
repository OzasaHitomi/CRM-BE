from crm_be.schemas.v1.request.base import (
    BaseV1RequestSchema,
    BoundedEmailStr,
    PasswordStr,
    TrimmedStr100,
)
from crm_be.store.enums.account_type import AccountType


class CreateUserRequest(BaseV1RequestSchema):
    name: TrimmedStr100
    email: BoundedEmailStr
    password: PasswordStr
    role: AccountType


class UpdateUserStatusRequest(BaseV1RequestSchema):
    is_active: bool
