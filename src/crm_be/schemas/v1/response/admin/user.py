import uuid

from crm_be.schemas.v1.response.base import BaseV1ResponseSchema


class CreateUserResponse(BaseV1ResponseSchema):
    user_id: uuid.UUID
    name: str
    email: str
    role: str


class GetUsersResponseItem(BaseV1ResponseSchema):
    user_id: uuid.UUID
    name: str
    email: str
    role: str
    is_active: bool


class UpdateUserStatusResponse(BaseV1ResponseSchema):
    user_id: uuid.UUID
    is_active: bool
