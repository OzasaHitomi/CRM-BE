from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest

from freezegun import freeze_time

from crm_be.core.config.base import core_settings
from crm_be.logic.security.jwt import create_access_token, verify_jwt_token
from crm_be.logic.security.types import AccessTokenPayload
from crm_be.store.enums.account_type import AccountType


class TestCreateAccessToken:
    def test_returns_str(self) -> None:
        token = create_access_token(uuid4(), AccountType.sales, "テストユーザー")

        assert isinstance(token, str)

    def test_sub_matches_user_id(self) -> None:
        user_id = uuid4()

        token = create_access_token(user_id, AccountType.sales, "テストユーザー")

        decoded = jwt.decode(
            token, core_settings.secret_key, algorithms=[core_settings.jwt_algorithm]
        )
        assert decoded["sub"] == str(user_id)

    def test_type_is_access(self) -> None:
        token = create_access_token(uuid4(), AccountType.sales, "テストユーザー")

        decoded = jwt.decode(
            token, core_settings.secret_key, algorithms=[core_settings.jwt_algorithm]
        )
        assert decoded["type"] == "access"

    def test_role_matches_input_role(self) -> None:
        token = create_access_token(uuid4(), AccountType.admin, "テストユーザー")

        decoded = jwt.decode(
            token, core_settings.secret_key, algorithms=[core_settings.jwt_algorithm]
        )
        assert decoded["role"] == AccountType.admin.value

    def test_name_matches_input_name(self) -> None:
        token = create_access_token(uuid4(), AccountType.sales, "山田太郎")

        decoded = jwt.decode(
            token, core_settings.secret_key, algorithms=[core_settings.jwt_algorithm]
        )
        assert decoded["name"] == "山田太郎"

    @freeze_time("2026-07-09 12:00:00")
    def test_exp_matches_configured_expiry(self) -> None:
        token = create_access_token(uuid4(), AccountType.sales, "テストユーザー")

        decoded = jwt.decode(
            token, core_settings.secret_key, algorithms=[core_settings.jwt_algorithm]
        )
        expected_exp = datetime.now(UTC) + timedelta(
            minutes=core_settings.access_token_expire_minutes
        )
        assert decoded["exp"] == int(expected_exp.timestamp())

    def test_sub_differs_for_different_user_ids(self) -> None:
        token_a = create_access_token(uuid4(), AccountType.sales, "テストユーザー")
        token_b = create_access_token(uuid4(), AccountType.sales, "テストユーザー")

        decoded_a = jwt.decode(
            token_a, core_settings.secret_key, algorithms=[core_settings.jwt_algorithm]
        )
        decoded_b = jwt.decode(
            token_b, core_settings.secret_key, algorithms=[core_settings.jwt_algorithm]
        )
        assert decoded_a["sub"] != decoded_b["sub"]

    def test_fails_to_decode_with_wrong_secret_key(self) -> None:
        token = create_access_token(uuid4(), AccountType.sales, "テストユーザー")

        with pytest.raises(jwt.InvalidSignatureError):
            jwt.decode(
                token,
                "wrong-secret-key-that-is-at-least-32-bytes-long",
                algorithms=[core_settings.jwt_algorithm],
            )

    def test_raises_expired_signature_error_after_expiry(self) -> None:
        with freeze_time("2026-07-09 12:00:00") as frozen_time:
            token = create_access_token(uuid4(), AccountType.sales, "テストユーザー")

            frozen_time.tick(
                delta=timedelta(minutes=core_settings.access_token_expire_minutes, seconds=1)
            )

            with pytest.raises(jwt.ExpiredSignatureError):
                jwt.decode(
                    token, core_settings.secret_key, algorithms=[core_settings.jwt_algorithm]
                )

    def test_fails_to_decode_with_wrong_algorithm(self) -> None:
        token = create_access_token(uuid4(), AccountType.sales, "テストユーザー")

        with pytest.raises(jwt.InvalidAlgorithmError):
            jwt.decode(token, core_settings.secret_key, algorithms=["HS512"])


class TestVerifyJwtToken:
    def test_returns_access_token_payload(self) -> None:
        token = create_access_token(uuid4(), AccountType.sales, "テストユーザー")

        payload = verify_jwt_token(token)

        assert isinstance(payload, AccessTokenPayload)

    def test_sub_matches_user_id(self) -> None:
        user_id = uuid4()
        token = create_access_token(user_id, AccountType.sales, "テストユーザー")

        payload = verify_jwt_token(token)

        assert payload.sub == user_id

    def test_type_is_access(self) -> None:
        token = create_access_token(uuid4(), AccountType.sales, "テストユーザー")

        payload = verify_jwt_token(token)

        assert payload.type == "access"

    def test_role_matches_input_role(self) -> None:
        token = create_access_token(uuid4(), AccountType.manager, "テストユーザー")

        payload = verify_jwt_token(token)

        assert payload.role == AccountType.manager

    def test_name_matches_input_name(self) -> None:
        token = create_access_token(uuid4(), AccountType.sales, "山田太郎")

        payload = verify_jwt_token(token)

        assert payload.name == "山田太郎"

    @freeze_time("2026-07-09 12:00:00")
    def test_exp_matches_configured_expiry(self) -> None:
        token = create_access_token(uuid4(), AccountType.sales, "テストユーザー")

        payload = verify_jwt_token(token)

        expected_exp = datetime.now(UTC) + timedelta(
            minutes=core_settings.access_token_expire_minutes
        )
        assert payload.exp == expected_exp

    def test_raises_invalid_signature_error_for_tampered_token(self) -> None:
        tampered_token = jwt.encode(
            {
                "sub": str(uuid4()),
                "exp": datetime.now(UTC) + timedelta(minutes=30),
                "type": "access",
                "role": AccountType.sales.value,
                "name": "テストユーザー",
            },
            "wrong-secret-key-that-is-at-least-32-bytes-long",
            algorithm=core_settings.jwt_algorithm,
        )

        with pytest.raises(jwt.InvalidSignatureError):
            verify_jwt_token(tampered_token)

    def test_raises_expired_signature_error_after_expiry(self) -> None:
        with freeze_time("2026-07-09 12:00:00") as frozen_time:
            token = create_access_token(uuid4(), AccountType.sales, "テストユーザー")

            frozen_time.tick(
                delta=timedelta(minutes=core_settings.access_token_expire_minutes, seconds=1)
            )

            with pytest.raises(jwt.ExpiredSignatureError):
                verify_jwt_token(token)
