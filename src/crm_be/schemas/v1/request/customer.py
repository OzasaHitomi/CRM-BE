from crm_be.schemas.v1.request.base import (
    BaseV1RequestSchema,
    BoundedEmailStr,
    PositiveDatabaseInt,
    TrimmedStr20,
    TrimmedStr100,
)
from crm_be.store.enums.industry_type import IndustryType


class CreateCustomerRequest(BaseV1RequestSchema):
    company_name: TrimmedStr100
    industry: IndustryType
    company_size: PositiveDatabaseInt
    contact_name: TrimmedStr100
    phone: TrimmedStr20
    email: BoundedEmailStr


class UpdateCustomerRequest(BaseV1RequestSchema):
    company_name: TrimmedStr100
    industry: IndustryType
    company_size: PositiveDatabaseInt
    contact_name: TrimmedStr100
    phone: TrimmedStr20
    email: BoundedEmailStr
