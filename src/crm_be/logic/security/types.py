from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from crm_be.store.constants.auth import ACCESS_TOKEN_TYPE
from crm_be.store.enums.account_type import AccountType


class BaseTokenPayload(BaseModel):
    sub: UUID
    exp: datetime


class AccessTokenPayload(BaseTokenPayload):
    type: Literal["access"] = ACCESS_TOKEN_TYPE
    name: str
    role: AccountType
