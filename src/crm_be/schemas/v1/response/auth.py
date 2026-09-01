import uuid

from crm_be.schemas.v1.response.base import BaseV1ResponseSchema


class MeResponse(BaseV1ResponseSchema):
    user_id: uuid.UUID
    role: str
    name: str
