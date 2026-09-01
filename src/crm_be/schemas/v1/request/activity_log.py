from datetime import date

from crm_be.schemas.v1.request.base import BaseV1RequestSchema
from crm_be.store.enums.activity_type import ActivityType


class CreateActivityLogRequest(BaseV1RequestSchema):
    type: ActivityType
    activity_date: date
    note: str | None = None


class UpdateActivityLogRequest(BaseV1RequestSchema):
    type: ActivityType
    activity_date: date
    note: str | None = None
