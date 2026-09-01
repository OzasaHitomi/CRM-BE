import uuid

from datetime import date

from crm_be.schemas.v1.response.base import BaseV1ResponseSchema
from crm_be.store.enums.activity_type import ActivityType


class CreateActivityLogResponse(BaseV1ResponseSchema):
    activity_log_id: uuid.UUID
    type: ActivityType
    activity_date: date
    note: str | None


class UpdateActivityLogResponse(BaseV1ResponseSchema):
    activity_log_id: uuid.UUID
    type: ActivityType
    activity_date: date
    note: str | None
