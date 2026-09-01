from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import jwt
import pytest

from fastapi import HTTPException
from sqlalchemy.orm import Session

from crm_be.api.common.dependencies.authentication import get_current_user, verify_access_token
from crm_be.core.config.base import core_settings
from crm_be.logic.security.jwt import create_access_token
from crm_be.store.enums.account_type import AccountType
from tests.factories.user import create_user


class TestVerifyAccessToken:
    def test_returns_payload_for_valid_token(self) -> None:
        user_id = uuid4()
        token = create_access_token(user_id, AccountType.sales, "テストユーザー")

        payload = verify_access_token(token)

        assert payload.sub == user_id

    def test_raises_when_cookie_is_missing(self) -> None:
        with pytest.raises(HTTPException) as exc_info:
            verify_access_token(None)

        assert exc_info.value.status_code == 401

    def test_raises_when_token_is_expired(self) -> None:
        expired_token = jwt.encode(
            {
                "sub": str(uuid4()),
                "exp": datetime.now(UTC) - timedelta(minutes=1),
                "type": "access",
                "role": AccountType.sales.value,
                "name": "テストユーザー",
            },
            core_settings.secret_key,
            algorithm=core_settings.jwt_algorithm,
        )

        with pytest.raises(HTTPException) as exc_info:
            verify_access_token(expired_token)

        assert exc_info.value.status_code == 401

    def test_raises_when_token_is_invalid(self) -> None:
        with pytest.raises(HTTPException) as exc_info:
            verify_access_token("invalid-token")

        assert exc_info.value.status_code == 401


class TestGetCurrentUser:
    def test_returns_user_when_active(self, db_session: Session) -> None:
        user = create_user(db_session, email="get_current_user_active@example.com")
        payload = verify_access_token(
            create_access_token(UUID(user.id), user.account_type, user.name)
        )

        result = get_current_user(payload, db_session)

        assert result.id == user.id

    def test_raises_when_user_not_found(self, db_session: Session) -> None:
        payload = verify_access_token(
            create_access_token(uuid4(), AccountType.sales, "テストユーザー")
        )

        with pytest.raises(HTTPException) as exc_info:
            get_current_user(payload, db_session)

        assert exc_info.value.status_code == 401

    def test_raises_when_user_is_inactive(self, db_session: Session) -> None:
        user = create_user(
            db_session, email="get_current_user_inactive@example.com", is_active=False
        )
        payload = verify_access_token(
            create_access_token(UUID(user.id), user.account_type, user.name)
        )

        with pytest.raises(HTTPException) as exc_info:
            get_current_user(payload, db_session)

        assert exc_info.value.status_code == 401
