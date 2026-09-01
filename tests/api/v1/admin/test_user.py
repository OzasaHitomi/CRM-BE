import uuid

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from crm_be.logic.security.password import verify_password
from crm_be.repositories.user.repository import get_user_by_email, get_user_by_id
from crm_be.store.enums.account_type import AccountType
from tests.factories.auth import create_and_login_as
from tests.factories.user import create_user


class TestCreateUser:
    def test_creates_user_when_admin(self, client: TestClient, db_session: Session) -> None:
        create_and_login_as(
            client, db_session, email="admin_success@example.com", account_type=AccountType.admin
        )

        response = client.post(
            "/api/v1/admin/users",
            json={
                "name": "新規ユーザー",
                "email": "new_user@example.com",
                "password": "password",
                "role": "sales",
            },
        )

        assert response.status_code == 201
        body = response.json()
        assert body["name"] == "新規ユーザー"
        assert body["email"] == "new_user@example.com"
        assert body["role"] == "sales"

    def test_persists_hashed_password(self, client: TestClient, db_session: Session) -> None:
        create_and_login_as(
            client, db_session, email="admin_persist@example.com", account_type=AccountType.admin
        )

        client.post(
            "/api/v1/admin/users",
            json={
                "name": "新規ユーザー",
                "email": "persisted_user@example.com",
                "password": "password",
                "role": "sales",
            },
        )

        created_user = get_user_by_email(db_session, "persisted_user@example.com")
        assert created_user is not None
        assert verify_password("password", created_user.hashed_password)

    def test_fails_when_not_admin(self, client: TestClient, db_session: Session) -> None:
        create_and_login_as(
            client, db_session, email="sales_forbidden@example.com", account_type=AccountType.sales
        )

        response = client.post(
            "/api/v1/admin/users",
            json={
                "name": "新規ユーザー",
                "email": "blocked_user@example.com",
                "password": "password",
                "role": "sales",
            },
        )

        assert response.status_code == 403

    def test_fails_when_not_logged_in(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/admin/users",
            json={
                "name": "新規ユーザー",
                "email": "anonymous_user@example.com",
                "password": "password",
                "role": "sales",
            },
        )

        assert response.status_code == 401

    def test_fails_when_role_is_admin(self, client: TestClient, db_session: Session) -> None:
        create_and_login_as(
            client,
            db_session,
            email="admin_reject_admin@example.com",
            account_type=AccountType.admin,
        )

        response = client.post(
            "/api/v1/admin/users",
            json={
                "name": "新規管理者",
                "email": "new_admin@example.com",
                "password": "password",
                "role": "admin",
            },
        )

        assert response.status_code == 422
        assert get_user_by_email(db_session, "new_admin@example.com") is None

    def test_fails_when_email_already_registered(
        self, client: TestClient, db_session: Session
    ) -> None:
        create_and_login_as(
            client, db_session, email="admin_duplicate@example.com", account_type=AccountType.admin
        )
        existing_user = create_user(db_session, email="already_registered@example.com")

        response = client.post(
            "/api/v1/admin/users",
            json={
                "name": "重複ユーザー",
                "email": existing_user.email,
                "password": "password",
                "role": "sales",
            },
        )

        assert response.status_code == 422


class TestGetUsers:
    def test_excludes_admin_accounts(self, client: TestClient, db_session: Session) -> None:
        create_and_login_as(
            client, db_session, email="admin_list@example.com", account_type=AccountType.admin
        )
        create_user(db_session, email="admin_other@example.com", account_type=AccountType.admin)
        sales_user = create_user(
            db_session, email="sales_list@example.com", account_type=AccountType.sales
        )
        manager_user = create_user(
            db_session, email="manager_list@example.com", account_type=AccountType.manager
        )

        response = client.get("/api/v1/admin/users")

        assert response.status_code == 200
        emails = {item["email"] for item in response.json()}
        assert emails == {sales_user.email, manager_user.email}

    def test_orders_by_created_at_descending(self, client: TestClient, db_session: Session) -> None:
        create_and_login_as(
            client, db_session, email="admin_order@example.com", account_type=AccountType.admin
        )
        now = datetime.now(UTC)
        older_user = create_user(
            db_session, email="older_user@example.com", created_at=now - timedelta(days=1)
        )
        newer_user = create_user(db_session, email="newer_user@example.com", created_at=now)

        response = client.get("/api/v1/admin/users")

        emails = [item["email"] for item in response.json()]
        assert emails.index(newer_user.email) < emails.index(older_user.email)

    def test_includes_is_active_status(self, client: TestClient, db_session: Session) -> None:
        create_and_login_as(
            client, db_session, email="admin_status@example.com", account_type=AccountType.admin
        )
        active_user = create_user(db_session, email="active_list@example.com", is_active=True)
        suspended_user = create_user(
            db_session, email="suspended_list@example.com", is_active=False
        )

        response = client.get("/api/v1/admin/users")

        assert response.status_code == 200
        statuses = {item["email"]: item["isActive"] for item in response.json()}
        assert statuses[active_user.email] is True
        assert statuses[suspended_user.email] is False

    def test_fails_when_not_admin(self, client: TestClient, db_session: Session) -> None:
        create_and_login_as(
            client,
            db_session,
            email="sales_list_forbidden@example.com",
            account_type=AccountType.sales,
        )

        response = client.get("/api/v1/admin/users")

        assert response.status_code == 403

    def test_fails_when_not_logged_in(self, client: TestClient) -> None:
        response = client.get("/api/v1/admin/users")

        assert response.status_code == 401


class TestUpdateUserStatus:
    def test_deactivates_target_user(self, client: TestClient, db_session: Session) -> None:
        create_and_login_as(
            client, db_session, email="admin_deactivate@example.com", account_type=AccountType.admin
        )
        target_user = create_user(db_session, email="target_deactivate@example.com", is_active=True)

        response = client.put(
            f"/api/v1/admin/users/status/{target_user.id}",
            json={"isActive": False},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["userId"] == target_user.id
        assert body["isActive"] is False

    def test_activates_target_user(self, client: TestClient, db_session: Session) -> None:
        create_and_login_as(
            client, db_session, email="admin_activate@example.com", account_type=AccountType.admin
        )
        target_user = create_user(db_session, email="target_activate@example.com", is_active=False)

        response = client.put(
            f"/api/v1/admin/users/status/{target_user.id}",
            json={"isActive": True},
        )

        assert response.status_code == 200
        assert response.json()["isActive"] is True

    def test_persists_status_change(self, client: TestClient, db_session: Session) -> None:
        create_and_login_as(
            client,
            db_session,
            email="admin_persist_status@example.com",
            account_type=AccountType.admin,
        )
        target_user = create_user(
            db_session, email="target_persist_status@example.com", is_active=True
        )

        client.put(
            f"/api/v1/admin/users/status/{target_user.id}",
            json={"isActive": False},
        )

        db_session.expire_all()
        persisted_user = get_user_by_id(db_session, uuid.UUID(target_user.id))
        assert persisted_user is not None
        assert persisted_user.is_active is False

    def test_fails_when_user_not_found(self, client: TestClient, db_session: Session) -> None:
        create_and_login_as(
            client, db_session, email="admin_not_found@example.com", account_type=AccountType.admin
        )

        response = client.put(
            f"/api/v1/admin/users/status/{uuid.uuid4()}",
            json={"isActive": False},
        )

        assert response.status_code == 404

    def test_fails_when_target_is_admin(self, client: TestClient, db_session: Session) -> None:
        create_and_login_as(
            client,
            db_session,
            email="admin_reject_target@example.com",
            account_type=AccountType.admin,
        )
        target_admin = create_user(
            db_session,
            email="target_admin@example.com",
            account_type=AccountType.admin,
            is_active=True,
        )

        response = client.put(
            f"/api/v1/admin/users/status/{target_admin.id}",
            json={"isActive": False},
        )

        assert response.status_code == 422
        persisted_user = get_user_by_id(db_session, uuid.UUID(target_admin.id))
        assert persisted_user is not None
        assert persisted_user.is_active is True

    def test_fails_when_target_is_self(self, client: TestClient, db_session: Session) -> None:
        admin_user = create_and_login_as(
            client, db_session, email="admin_self@example.com", account_type=AccountType.admin
        )

        response = client.put(
            f"/api/v1/admin/users/status/{admin_user.id}",
            json={"isActive": False},
        )

        assert response.status_code == 422

    def test_fails_when_not_admin(self, client: TestClient, db_session: Session) -> None:
        create_and_login_as(
            client,
            db_session,
            email="sales_update_forbidden@example.com",
            account_type=AccountType.sales,
        )
        target_user = create_user(db_session, email="target_forbidden@example.com", is_active=True)

        response = client.put(
            f"/api/v1/admin/users/status/{target_user.id}",
            json={"isActive": False},
        )

        assert response.status_code == 403
        persisted_user = get_user_by_id(db_session, uuid.UUID(target_user.id))
        assert persisted_user is not None
        assert persisted_user.is_active is True

    def test_fails_when_not_logged_in(self, client: TestClient, db_session: Session) -> None:
        target_user = create_user(db_session, email="target_anonymous@example.com")

        response = client.put(
            f"/api/v1/admin/users/status/{target_user.id}",
            json={"isActive": False},
        )

        assert response.status_code == 401

    def test_fails_when_is_active_missing(self, client: TestClient, db_session: Session) -> None:
        create_and_login_as(
            client,
            db_session,
            email="admin_invalid_body@example.com",
            account_type=AccountType.admin,
        )
        target_user = create_user(db_session, email="target_invalid_body@example.com")

        response = client.put(
            f"/api/v1/admin/users/status/{target_user.id}",
            json={},
        )

        assert response.status_code == 422
