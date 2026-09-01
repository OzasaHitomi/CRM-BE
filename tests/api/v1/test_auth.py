import jwt
import pytest

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from crm_be.core.config.base import core_settings
from tests.factories.auth import create_and_login_as
from tests.factories.user import create_user


class TestLogin:
    def test_success(self, client: TestClient, db_session: Session) -> None:
        user = create_user(db_session, email="login_success@example.com")

        response = client.post(
            "/api/v1/auth/login", json={"email": user.email, "password": "password"}
        )

        assert response.status_code == 204
        assert "access_token" in response.cookies

    def test_fails_when_email_not_registered(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "not_registered@example.com", "password": "password"},
        )

        assert response.status_code == 401
        assert "access_token" not in response.cookies

    def test_fails_when_password_is_incorrect(
        self, client: TestClient, db_session: Session
    ) -> None:
        user = create_user(db_session, email="wrong_password@example.com")

        response = client.post(
            "/api/v1/auth/login", json={"email": user.email, "password": "wrong_password"}
        )

        assert response.status_code == 401
        assert "access_token" not in response.cookies

    def test_fails_when_user_is_inactive(self, client: TestClient, db_session: Session) -> None:
        user = create_user(db_session, email="inactive@example.com", is_active=False)

        response = client.post(
            "/api/v1/auth/login", json={"email": user.email, "password": "password"}
        )

        assert response.status_code == 403
        assert "access_token" not in response.cookies

    def test_sets_access_token_cookie_with_secure_attributes(
        self, client: TestClient, db_session: Session
    ) -> None:
        user = create_user(db_session, email="cookie_attributes@example.com")

        response = client.post(
            "/api/v1/auth/login", json={"email": user.email, "password": "password"}
        )

        set_cookie_header = response.headers["set-cookie"]
        assert "HttpOnly" in set_cookie_header
        assert "samesite=lax" in set_cookie_header.lower()

    def test_sets_secure_cookie_in_production(
        self,
        client: TestClient,
        db_session: Session,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        user = create_user(db_session, email="secure_cookie@example.com")
        monkeypatch.setattr(core_settings, "cookie_secure", True)

        response = client.post(
            "/api/v1/auth/login", json={"email": user.email, "password": "password"}
        )

        assert "Secure" in response.headers["set-cookie"]

    def test_rejects_password_longer_than_bcrypt_limit(
        self, client: TestClient, db_session: Session
    ) -> None:
        user = create_user(db_session, email="long_password@example.com")

        response = client.post(
            "/api/v1/auth/login",
            json={"email": user.email, "password": "a" * 73},
        )

        assert response.status_code == 422

    def test_issues_jwt_with_user_id_as_subject(
        self, client: TestClient, db_session: Session
    ) -> None:
        user = create_user(db_session, email="jwt_subject@example.com")

        response = client.post(
            "/api/v1/auth/login", json={"email": user.email, "password": "password"}
        )

        access_token = response.cookies["access_token"]
        payload = jwt.decode(
            access_token, core_settings.secret_key, algorithms=[core_settings.jwt_algorithm]
        )

        assert payload["sub"] == user.id
        assert payload["type"] == "access"


class TestMe:
    def test_returns_current_user(self, client: TestClient, db_session: Session) -> None:
        user = create_and_login_as(client, db_session, email="me_success@example.com")

        response = client.get("/api/v1/auth/me")

        assert response.status_code == 200
        assert response.json() == {
            "userId": user.id,
            "role": user.account_type.value,
            "name": user.name,
        }

    def test_fails_when_not_logged_in(self, client: TestClient) -> None:
        response = client.get("/api/v1/auth/me")

        assert response.status_code == 401

    def test_returns_role_from_token_even_if_user_becomes_inactive_after_login(
        self, client: TestClient, db_session: Session
    ) -> None:
        """/meはトークンの内容のみを返すため、ログイン後にユーザーが非アクティブ化されてもトークンの有効期限内は200を返し続ける(意図した挙動)"""
        user = create_user(db_session, email="me_inactive_after_login@example.com")
        client.post("/api/v1/auth/login", json={"email": user.email, "password": "password"})

        user.is_active = False
        db_session.commit()

        response = client.get("/api/v1/auth/me")

        assert response.status_code == 200
        assert response.json() == {
            "userId": user.id,
            "role": user.account_type.value,
            "name": user.name,
        }


class TestLogout:
    def test_returns_no_content(self, client: TestClient) -> None:
        response = client.post("/api/v1/auth/logout")

        assert response.status_code == 204

    def test_clears_access_token_cookie(self, client: TestClient, db_session: Session) -> None:
        user = create_user(db_session, email="logout_clears_cookie@example.com")
        login_response = client.post(
            "/api/v1/auth/login", json={"email": user.email, "password": "password"}
        )
        assert "access_token" in login_response.cookies

        logout_response = client.post("/api/v1/auth/logout")

        assert logout_response.status_code == 204
        assert "Max-Age=0" in logout_response.headers["set-cookie"]

    def test_removes_access_token_from_cookie_jar(
        self, client: TestClient, db_session: Session
    ) -> None:
        create_and_login_as(client, db_session, email="logout_removes_cookie@example.com")

        response = client.post("/api/v1/auth/logout")

        assert response.status_code == 204
        assert client.cookies.get("access_token") is None


class TestSessionLifecycle:
    def test_invalidates_session_after_logout(
        self, client: TestClient, db_session: Session
    ) -> None:
        create_and_login_as(client, db_session, email="logout_invalidates@example.com")

        authenticated_response = client.get("/api/v1/auth/me")
        assert authenticated_response.status_code == 200

        logout_response = client.post("/api/v1/auth/logout")
        assert logout_response.status_code == 204

        response_after_logout = client.get("/api/v1/auth/me")

        assert response_after_logout.status_code == 401
        assert "access_token" not in client.cookies
