from crm_be.schemas.v1.request.base import (
    BaseV1RequestSchema,
    PositiveDatabaseInt,
    TrimmedStr100,
)
from crm_be.store.enums.deal_plan import DealPlan
from crm_be.store.enums.deal_status import DealStatus


class CreateDealRequest(BaseV1RequestSchema):
    title: TrimmedStr100
    amount: PositiveDatabaseInt
    plan: DealPlan
    license_count: PositiveDatabaseInt
    contract_period: PositiveDatabaseInt


class UpdateDealRequest(BaseV1RequestSchema):
    title: TrimmedStr100
    amount: PositiveDatabaseInt
    plan: DealPlan
    license_count: PositiveDatabaseInt
    contract_period: PositiveDatabaseInt


class UpdateDealStatusRequest(BaseV1RequestSchema):
    status: DealStatus
