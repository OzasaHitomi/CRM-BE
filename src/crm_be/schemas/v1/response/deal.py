import uuid

from crm_be.schemas.v1.response.base import BaseV1ResponseSchema
from crm_be.store.enums.deal_plan import DealPlan
from crm_be.store.enums.deal_status import DealStatus


class UpdateDealResponse(BaseV1ResponseSchema):
    deal_id: uuid.UUID
    title: str
    amount: int
    plan: DealPlan
    license_count: int
    contract_period: int


class UpdateDealStatusResponse(BaseV1ResponseSchema):
    deal_id: uuid.UUID
    status: DealStatus
