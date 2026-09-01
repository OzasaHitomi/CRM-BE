from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt

from crm_be.core.config.base import core_settings
from crm_be.logic.security.types import AccessTokenPayload
from crm_be.store.enums.account_type import AccountType


def create_access_token(user_id: UUID, role: AccountType, name: str) -> str:
    """アクセストークンを作成する関数"""
    expire = datetime.now(UTC) + timedelta(minutes=core_settings.access_token_expire_minutes)
    payload = AccessTokenPayload(sub=user_id, exp=expire, role=role, name=name)
    return jwt.encode(
        {
            "sub": str(payload.sub),
            "type": payload.type,
            "role": payload.role.value,
            "name": payload.name,
            "exp": payload.exp,
        },
        core_settings.secret_key,
        algorithm=core_settings.jwt_algorithm,
    )


def verify_jwt_token(token: str) -> AccessTokenPayload:
    """JWTトークンを検証する関数"""
    decoded = jwt.decode(token, core_settings.secret_key, algorithms=[core_settings.jwt_algorithm])
    return AccessTokenPayload.model_validate(decoded)
