import uuid

from datetime import date, datetime

from crm_be.schemas.v1.response.base import BaseV1ResponseSchema
from crm_be.store.enums.activity_type import ActivityType
from crm_be.store.enums.deal_plan import DealPlan
from crm_be.store.enums.deal_status import DealStatus
from crm_be.store.enums.industry_type import IndustryType


class AssignedUserResponseItem(BaseV1ResponseSchema):
    user_id: uuid.UUID
    name: str


class ActivityLogResponseItem(BaseV1ResponseSchema):
    activity_log_id: uuid.UUID
    type: ActivityType
    activity_date: date
    note: str | None


class DealResponseItem(BaseV1ResponseSchema):
    deal_id: uuid.UUID
    title: str
    status: DealStatus
    amount: int
    plan: DealPlan
    license_count: int
    contract_period: int
    created_at: datetime
    activity_logs: list[ActivityLogResponseItem]


class CreateCustomerResponse(BaseV1ResponseSchema):
    customer_id: uuid.UUID
    company_name: str
    industry: IndustryType
    company_size: int
    contact_name: str
    phone: str
    email: str
    assigned_user: AssignedUserResponseItem | None


class GetCustomersResponseItem(BaseV1ResponseSchema):
    customer_id: uuid.UUID
    company_name: str
    industry: IndustryType
    assigned_user: AssignedUserResponseItem | None


class GetCustomerResponse(BaseV1ResponseSchema):
    customer_id: uuid.UUID
    company_name: str
    industry: IndustryType
    company_size: int
    contact_name: str
    phone: str
    email: str
    assigned_user: AssignedUserResponseItem | None
    deals: list[DealResponseItem]


class AssignCustomerUserResponse(BaseV1ResponseSchema):
    customer_id: uuid.UUID
    assigned_user: AssignedUserResponseItem


class UpdateCustomerResponse(BaseV1ResponseSchema):
    customer_id: uuid.UUID
    company_name: str
    industry: IndustryType
    company_size: int
    contact_name: str
    phone: str
    email: str
    assigned_user: AssignedUserResponseItem | None
