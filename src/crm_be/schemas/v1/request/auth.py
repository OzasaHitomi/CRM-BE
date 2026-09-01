from crm_be.schemas.v1.request.base import BaseV1RequestSchema, BoundedEmailStr, PasswordStr


class LoginRequest(BaseV1RequestSchema):
    email: BoundedEmailStr
    password: PasswordStr
