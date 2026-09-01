import uuid

from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from crm_be.models.activity_log import ActivityLog
from crm_be.models.customer import Customer
from crm_be.models.deal import Deal
from crm_be.repositories.customer.repository import create_customer
from crm_be.store.enums.account_type import AccountType
from crm_be.store.enums.activity_type import ActivityType
from crm_be.store.enums.deal_plan import DealPlan
from crm_be.store.enums.deal_status import DealStatus
from crm_be.store.enums.industry_type import IndustryType
from tests.factories.auth import create_and_login_as
from tests.factories.user import create_user


def make_customer(db_session: Session, **override: object) -> Customer:
    defaults: dict[str, object] = {
        "id": str(uuid.uuid4()),
        "company_name": "テスト株式会社",
        "industry": IndustryType.technology,
        "company_size": 100,
        "contact_name": "山田太郎",
        "phone": "03-1234-5678",
        "email": f"customer_{uuid.uuid4().hex[:8]}@example.com",
    }
    defaults.update(override)
    return create_customer(db_session, Customer(**defaults))


def make_deal(db_session: Session, customer_id: str, **override: object) -> Deal:
    defaults: dict[str, object] = {
        "id": str(uuid.uuid4()),
        "customer_id": customer_id,
        "title": "商談",
        "status": DealStatus.lead,
        "amount": 1000,
        "plan": DealPlan.starter,
        "license_count": 1,
        "contract_period": 12,
    }
    defaults.update(override)
    deal = Deal(**defaults)
    db_session.add(deal)
    db_session.commit()
    db_session.refresh(deal)
    return deal


def make_activity_log(db_session: Session, deal_id: str, **override: object) -> ActivityLog:
    defaults: dict[str, object] = {
        "id": str(uuid.uuid4()),
        "deal_id": deal_id,
        "type": ActivityType.call,
        "activity_date": date.today(),
        "note": "架電しました",
    }
    defaults.update(override)
    log = ActivityLog(**defaults)
    db_session.add(log)
    db_session.commit()
    db_session.refresh(log)
    return log


def build_activity_log_payload(**override: object) -> dict:
    defaults: dict[str, object] = {
        "type": "call",
        "activityDate": date.today().isoformat(),
        "note": "架電しました",
    }
    defaults.update(override)
    return defaults


def build_update_deal_payload(**override: object) -> dict:
    defaults: dict[str, object] = {
        "title": "A社商談",
        "amount": 5000,
        "plan": "enterprise",
        "licenseCount": 10,
        "contractPeriod": 24,
    }
    defaults.update(override)
    return defaults


class TestCreateActivityLog:
    def test_sales_can_create_for_own_deal(self, client: TestClient, db_session: Session) -> None:
        sales_user = create_and_login_as(
            client,
            db_session,
            email="sales_create_activity_log_own@example.com",
            account_type=AccountType.sales,
        )
        customer = make_customer(db_session, assigned_user_id=sales_user.id)
        deal = make_deal(db_session, customer.id)

        response = client.post(
            f"/api/v1/deals/{deal.id}/activity-logs", json=build_activity_log_payload()
        )

        assert response.status_code == 201

    def test_manager_can_create_for_other_users_deal(
        self, client: TestClient, db_session: Session
    ) -> None:
        create_and_login_as(
            client,
            db_session,
            email="manager_create_activity_log_other@example.com",
            account_type=AccountType.manager,
        )
        sales_user = create_user(
            db_session, email="sales_owner_for_manager_activity_log@example.com"
        )
        customer = make_customer(db_session, assigned_user_id=sales_user.id)
        deal = make_deal(db_session, customer.id)

        response = client.post(
            f"/api/v1/deals/{deal.id}/activity-logs", json=build_activity_log_payload()
        )

        assert response.status_code == 201

    def test_allows_creation_on_closed_won_deal(
        self, client: TestClient, db_session: Session
    ) -> None:
        create_and_login_as(
            client,
            db_session,
            email="manager_create_activity_log_closed_won@example.com",
            account_type=AccountType.manager,
        )
        customer = make_customer(db_session)
        deal = make_deal(db_session, customer.id, status=DealStatus.closed_won)

        response = client.post(
            f"/api/v1/deals/{deal.id}/activity-logs", json=build_activity_log_payload()
        )

        assert response.status_code == 201

    def test_allows_creation_on_closed_lost_deal(
        self, client: TestClient, db_session: Session
    ) -> None:
        create_and_login_as(
            client,
            db_session,
            email="manager_create_activity_log_closed_lost@example.com",
            account_type=AccountType.manager,
        )
        customer = make_customer(db_session)
        deal = make_deal(db_session, customer.id, status=DealStatus.closed_lost)

        response = client.post(
            f"/api/v1/deals/{deal.id}/activity-logs", json=build_activity_log_payload()
        )

        assert response.status_code == 201

    def test_fails_when_admin(self, client: TestClient, db_session: Session) -> None:
        create_and_login_as(
            client,
            db_session,
            email="admin_create_activity_log_forbidden@example.com",
            account_type=AccountType.admin,
        )
        customer = make_customer(db_session)
        deal = make_deal(db_session, customer.id)

        response = client.post(
            f"/api/v1/deals/{deal.id}/activity-logs", json=build_activity_log_payload()
        )

        assert response.status_code == 403

    def test_sales_forbidden_for_other_users_deal(
        self, client: TestClient, db_session: Session
    ) -> None:
        create_and_login_as(
            client,
            db_session,
            email="sales_create_activity_log_other@example.com",
            account_type=AccountType.sales,
        )
        other_sales_user = create_user(
            db_session, email="other_sales_owner_activity_log@example.com"
        )
        customer = make_customer(db_session, assigned_user_id=other_sales_user.id)
        deal = make_deal(db_session, customer.id)

        response = client.post(
            f"/api/v1/deals/{deal.id}/activity-logs", json=build_activity_log_payload()
        )

        assert response.status_code == 403

    def test_fails_when_deal_not_found(self, client: TestClient, db_session: Session) -> None:
        create_and_login_as(
            client,
            db_session,
            email="manager_create_activity_log_missing@example.com",
            account_type=AccountType.manager,
        )

        response = client.post(
            f"/api/v1/deals/{uuid.uuid4()}/activity-logs", json=build_activity_log_payload()
        )

        assert response.status_code == 404

    def test_fails_when_not_logged_in(self, client: TestClient, db_session: Session) -> None:
        customer = make_customer(db_session)
        deal = make_deal(db_session, customer.id)

        response = client.post(
            f"/api/v1/deals/{deal.id}/activity-logs", json=build_activity_log_payload()
        )

        assert response.status_code == 401

    def test_fails_when_required_field_missing(
        self, client: TestClient, db_session: Session
    ) -> None:
        create_and_login_as(
            client,
            db_session,
            email="manager_create_activity_log_missing_field@example.com",
            account_type=AccountType.manager,
        )
        customer = make_customer(db_session)
        deal = make_deal(db_session, customer.id)
        payload = build_activity_log_payload()
        del payload["type"]

        response = client.post(f"/api/v1/deals/{deal.id}/activity-logs", json=payload)

        assert response.status_code == 422

    def test_fails_when_type_is_invalid(self, client: TestClient, db_session: Session) -> None:
        create_and_login_as(
            client,
            db_session,
            email="manager_create_activity_log_invalid_type@example.com",
            account_type=AccountType.manager,
        )
        customer = make_customer(db_session)
        deal = make_deal(db_session, customer.id)

        response = client.post(
            f"/api/v1/deals/{deal.id}/activity-logs",
            json=build_activity_log_payload(type="invalid_type"),
        )

        assert response.status_code == 422

    def test_response_matches_request_fields(self, client: TestClient, db_session: Session) -> None:
        create_and_login_as(
            client,
            db_session,
            email="manager_create_activity_log_fields@example.com",
            account_type=AccountType.manager,
        )
        customer = make_customer(db_session)
        deal = make_deal(db_session, customer.id)
        payload = build_activity_log_payload(
            type="visit", activityDate="2026-07-01", note="訪問しました"
        )

        response = client.post(f"/api/v1/deals/{deal.id}/activity-logs", json=payload)

        assert response.status_code == 201
        body = response.json()
        assert body["type"] == "visit"
        assert body["activityDate"] == "2026-07-01"
        assert body["note"] == "訪問しました"

    def test_note_is_null_when_omitted(self, client: TestClient, db_session: Session) -> None:
        create_and_login_as(
            client,
            db_session,
            email="manager_create_activity_log_null_note@example.com",
            account_type=AccountType.manager,
        )
        customer = make_customer(db_session)
        deal = make_deal(db_session, customer.id)
        payload = build_activity_log_payload()
        del payload["note"]

        response = client.post(f"/api/v1/deals/{deal.id}/activity-logs", json=payload)

        assert response.status_code == 201
        assert response.json()["note"] is None

    def test_persists_activity_log(self, client: TestClient, db_session: Session) -> None:
        create_and_login_as(
            client,
            db_session,
            email="manager_create_activity_log_persist@example.com",
            account_type=AccountType.manager,
        )
        customer = make_customer(db_session)
        deal = make_deal(db_session, customer.id)

        response = client.post(
            f"/api/v1/deals/{deal.id}/activity-logs",
            json=build_activity_log_payload(note="永続化テスト"),
        )

        activity_log_id = response.json()["activityLogId"]
        db_session.expire_all()
        persisted_activity_log = db_session.get(ActivityLog, activity_log_id)
        assert persisted_activity_log is not None
        assert persisted_activity_log.note == "永続化テスト"
        assert persisted_activity_log.deal_id == deal.id


class TestUpdateDeal:
    def test_sales_can_update_own_deal(self, client: TestClient, db_session: Session) -> None:
        sales_user = create_and_login_as(
            client,
            db_session,
            email="sales_update_deal_own@example.com",
            account_type=AccountType.sales,
        )
        customer = make_customer(db_session, assigned_user_id=sales_user.id)
        deal = make_deal(db_session, customer.id)

        response = client.put(f"/api/v1/deals/{deal.id}", json=build_update_deal_payload())

        assert response.status_code == 200

    def test_manager_can_update_other_users_deal(
        self, client: TestClient, db_session: Session
    ) -> None:
        create_and_login_as(
            client,
            db_session,
            email="manager_update_deal_other@example.com",
            account_type=AccountType.manager,
        )
        sales_user = create_user(
            db_session, email="sales_owner_for_manager_update_deal@example.com"
        )
        customer = make_customer(db_session, assigned_user_id=sales_user.id)
        deal = make_deal(db_session, customer.id)

        response = client.put(f"/api/v1/deals/{deal.id}", json=build_update_deal_payload())

        assert response.status_code == 200

    def test_fails_when_admin(self, client: TestClient, db_session: Session) -> None:
        create_and_login_as(
            client,
            db_session,
            email="admin_update_deal_forbidden@example.com",
            account_type=AccountType.admin,
        )
        customer = make_customer(db_session)
        deal = make_deal(db_session, customer.id)

        response = client.put(f"/api/v1/deals/{deal.id}", json=build_update_deal_payload())

        assert response.status_code == 403

    def test_sales_forbidden_for_other_users_deal(
        self, client: TestClient, db_session: Session
    ) -> None:
        create_and_login_as(
            client,
            db_session,
            email="sales_update_deal_other@example.com",
            account_type=AccountType.sales,
        )
        other_sales_user = create_user(
            db_session, email="other_sales_owner_update_deal@example.com"
        )
        customer = make_customer(db_session, assigned_user_id=other_sales_user.id)
        deal = make_deal(db_session, customer.id, title="元の商談")

        response = client.put(f"/api/v1/deals/{deal.id}", json=build_update_deal_payload())

        assert response.status_code == 403
        db_session.expire_all()
        persisted_deal = db_session.get(Deal, deal.id)
        assert persisted_deal is not None
        assert persisted_deal.title == "元の商談"

    def test_fails_when_deal_not_found(self, client: TestClient, db_session: Session) -> None:
        create_and_login_as(
            client,
            db_session,
            email="manager_update_deal_missing@example.com",
            account_type=AccountType.manager,
        )

        response = client.put(f"/api/v1/deals/{uuid.uuid4()}", json=build_update_deal_payload())

        assert response.status_code == 404

    def test_fails_when_not_logged_in(self, client: TestClient, db_session: Session) -> None:
        customer = make_customer(db_session)
        deal = make_deal(db_session, customer.id)

        response = client.put(f"/api/v1/deals/{deal.id}", json=build_update_deal_payload())

        assert response.status_code == 401

    def test_fails_when_required_field_missing(
        self, client: TestClient, db_session: Session
    ) -> None:
        create_and_login_as(
            client,
            db_session,
            email="manager_update_deal_missing_field@example.com",
            account_type=AccountType.manager,
        )
        customer = make_customer(db_session)
        deal = make_deal(db_session, customer.id)
        payload = build_update_deal_payload()
        del payload["title"]

        response = client.put(f"/api/v1/deals/{deal.id}", json=payload)

        assert response.status_code == 422

    def test_fails_when_plan_is_invalid(self, client: TestClient, db_session: Session) -> None:
        create_and_login_as(
            client,
            db_session,
            email="manager_update_deal_invalid_plan@example.com",
            account_type=AccountType.manager,
        )
        customer = make_customer(db_session)
        deal = make_deal(db_session, customer.id)

        response = client.put(
            f"/api/v1/deals/{deal.id}",
            json=build_update_deal_payload(plan="invalid_plan"),
        )

        assert response.status_code == 422

    def test_response_matches_request_fields(self, client: TestClient, db_session: Session) -> None:
        create_and_login_as(
            client,
            db_session,
            email="manager_update_deal_fields@example.com",
            account_type=AccountType.manager,
        )
        customer = make_customer(db_session)
        deal = make_deal(db_session, customer.id)

        response = client.put(
            f"/api/v1/deals/{deal.id}",
            json=build_update_deal_payload(
                title="B社商談",
                amount=8000,
                plan="professional",
                licenseCount=5,
                contractPeriod=12,
            ),
        )

        body = response.json()
        assert body["title"] == "B社商談"
        assert body["amount"] == 8000
        assert body["plan"] == "professional"
        assert body["licenseCount"] == 5
        assert body["contractPeriod"] == 12

    def test_persists_update(self, client: TestClient, db_session: Session) -> None:
        create_and_login_as(
            client,
            db_session,
            email="manager_update_deal_persist@example.com",
            account_type=AccountType.manager,
        )
        customer = make_customer(db_session)
        deal = make_deal(db_session, customer.id)

        client.put(
            f"/api/v1/deals/{deal.id}",
            json=build_update_deal_payload(title="永続化テスト商談"),
        )

        db_session.expire_all()
        persisted_deal = db_session.get(Deal, deal.id)
        assert persisted_deal is not None
        assert persisted_deal.title == "永続化テスト商談"


class TestUpdateDealStatus:
    def test_sales_can_update_own_deal_status(
        self, client: TestClient, db_session: Session
    ) -> None:
        sales_user = create_and_login_as(
            client,
            db_session,
            email="sales_update_deal_status_own@example.com",
            account_type=AccountType.sales,
        )
        customer = make_customer(db_session, assigned_user_id=sales_user.id)
        deal = make_deal(db_session, customer.id)

        response = client.put(f"/api/v1/deals/{deal.id}/status", json={"status": "negotiation"})

        assert response.status_code == 200

    def test_manager_can_update_other_users_deal_status(
        self, client: TestClient, db_session: Session
    ) -> None:
        create_and_login_as(
            client,
            db_session,
            email="manager_update_deal_status_other@example.com",
            account_type=AccountType.manager,
        )
        sales_user = create_user(
            db_session, email="sales_owner_for_manager_update_deal_status@example.com"
        )
        customer = make_customer(db_session, assigned_user_id=sales_user.id)
        deal = make_deal(db_session, customer.id)

        response = client.put(f"/api/v1/deals/{deal.id}/status", json={"status": "negotiation"})

        assert response.status_code == 200

    def test_fails_when_admin(self, client: TestClient, db_session: Session) -> None:
        create_and_login_as(
            client,
            db_session,
            email="admin_update_deal_status_forbidden@example.com",
            account_type=AccountType.admin,
        )
        customer = make_customer(db_session)
        deal = make_deal(db_session, customer.id)

        response = client.put(f"/api/v1/deals/{deal.id}/status", json={"status": "negotiation"})

        assert response.status_code == 403

    def test_sales_forbidden_for_other_users_deal(
        self, client: TestClient, db_session: Session
    ) -> None:
        create_and_login_as(
            client,
            db_session,
            email="sales_update_deal_status_other@example.com",
            account_type=AccountType.sales,
        )
        other_sales_user = create_user(
            db_session, email="other_sales_owner_update_deal_status@example.com"
        )
        customer = make_customer(db_session, assigned_user_id=other_sales_user.id)
        deal = make_deal(db_session, customer.id)

        response = client.put(f"/api/v1/deals/{deal.id}/status", json={"status": "negotiation"})

        assert response.status_code == 403

    def test_fails_when_deal_not_found(self, client: TestClient, db_session: Session) -> None:
        create_and_login_as(
            client,
            db_session,
            email="manager_update_deal_status_missing@example.com",
            account_type=AccountType.manager,
        )

        response = client.put(
            f"/api/v1/deals/{uuid.uuid4()}/status", json={"status": "negotiation"}
        )

        assert response.status_code == 404

    def test_fails_when_not_logged_in(self, client: TestClient, db_session: Session) -> None:
        customer = make_customer(db_session)
        deal = make_deal(db_session, customer.id)

        response = client.put(f"/api/v1/deals/{deal.id}/status", json={"status": "negotiation"})

        assert response.status_code == 401

    def test_fails_when_status_is_invalid(self, client: TestClient, db_session: Session) -> None:
        create_and_login_as(
            client,
            db_session,
            email="manager_update_deal_status_invalid@example.com",
            account_type=AccountType.manager,
        )
        customer = make_customer(db_session)
        deal = make_deal(db_session, customer.id)

        response = client.put(f"/api/v1/deals/{deal.id}/status", json={"status": "invalid_status"})

        assert response.status_code == 422

    def test_fails_when_deal_is_closed_won(self, client: TestClient, db_session: Session) -> None:
        create_and_login_as(
            client,
            db_session,
            email="manager_update_deal_status_closed_won@example.com",
            account_type=AccountType.manager,
        )
        customer = make_customer(db_session)
        deal = make_deal(db_session, customer.id, status=DealStatus.closed_won)

        response = client.put(f"/api/v1/deals/{deal.id}/status", json={"status": "closed_won"})

        assert response.status_code == 422

    def test_fails_when_deal_is_closed_lost(self, client: TestClient, db_session: Session) -> None:
        create_and_login_as(
            client,
            db_session,
            email="manager_update_deal_status_closed_lost@example.com",
            account_type=AccountType.manager,
        )
        customer = make_customer(db_session)
        deal = make_deal(db_session, customer.id, status=DealStatus.closed_lost)

        response = client.put(f"/api/v1/deals/{deal.id}/status", json={"status": "negotiation"})

        assert response.status_code == 422

    def test_response_matches_updated_status(self, client: TestClient, db_session: Session) -> None:
        create_and_login_as(
            client,
            db_session,
            email="manager_update_deal_status_fields@example.com",
            account_type=AccountType.manager,
        )
        customer = make_customer(db_session)
        deal = make_deal(db_session, customer.id)

        response = client.put(f"/api/v1/deals/{deal.id}/status", json={"status": "negotiation"})

        assert response.json()["status"] == "negotiation"

    def test_persists_status(self, client: TestClient, db_session: Session) -> None:
        create_and_login_as(
            client,
            db_session,
            email="manager_update_deal_status_persist@example.com",
            account_type=AccountType.manager,
        )
        customer = make_customer(db_session)
        deal = make_deal(db_session, customer.id)

        client.put(f"/api/v1/deals/{deal.id}/status", json={"status": "negotiation"})

        db_session.expire_all()
        persisted_deal = db_session.get(Deal, deal.id)
        assert persisted_deal is not None
        assert persisted_deal.status == DealStatus.negotiation


class TestUpdateActivityLog:
    def test_sales_can_update_own_activity_log(
        self, client: TestClient, db_session: Session
    ) -> None:
        sales_user = create_and_login_as(
            client,
            db_session,
            email="sales_update_activity_log_own@example.com",
            account_type=AccountType.sales,
        )
        customer = make_customer(db_session, assigned_user_id=sales_user.id)
        deal = make_deal(db_session, customer.id)
        log = make_activity_log(db_session, deal.id)

        response = client.put(
            f"/api/v1/deals/{deal.id}/activity-logs/{log.id}",
            json=build_activity_log_payload(),
        )

        assert response.status_code == 200

    def test_manager_can_update_other_users_activity_log(
        self, client: TestClient, db_session: Session
    ) -> None:
        create_and_login_as(
            client,
            db_session,
            email="manager_update_activity_log_other@example.com",
            account_type=AccountType.manager,
        )
        sales_user = create_user(
            db_session, email="sales_owner_for_manager_update_activity_log@example.com"
        )
        customer = make_customer(db_session, assigned_user_id=sales_user.id)
        deal = make_deal(db_session, customer.id)
        log = make_activity_log(db_session, deal.id)

        response = client.put(
            f"/api/v1/deals/{deal.id}/activity-logs/{log.id}",
            json=build_activity_log_payload(),
        )

        assert response.status_code == 200

    def test_allows_update_on_closed_won_deal(
        self, client: TestClient, db_session: Session
    ) -> None:
        create_and_login_as(
            client,
            db_session,
            email="manager_update_activity_log_closed_won@example.com",
            account_type=AccountType.manager,
        )
        customer = make_customer(db_session)
        deal = make_deal(db_session, customer.id, status=DealStatus.closed_won)
        log = make_activity_log(db_session, deal.id)

        response = client.put(
            f"/api/v1/deals/{deal.id}/activity-logs/{log.id}",
            json=build_activity_log_payload(),
        )

        assert response.status_code == 200

    def test_allows_update_on_closed_lost_deal(
        self, client: TestClient, db_session: Session
    ) -> None:
        create_and_login_as(
            client,
            db_session,
            email="manager_update_activity_log_closed_lost@example.com",
            account_type=AccountType.manager,
        )
        customer = make_customer(db_session)
        deal = make_deal(db_session, customer.id, status=DealStatus.closed_lost)
        log = make_activity_log(db_session, deal.id)

        response = client.put(
            f"/api/v1/deals/{deal.id}/activity-logs/{log.id}",
            json=build_activity_log_payload(),
        )

        assert response.status_code == 200

    def test_fails_when_admin(self, client: TestClient, db_session: Session) -> None:
        create_and_login_as(
            client,
            db_session,
            email="admin_update_activity_log_forbidden@example.com",
            account_type=AccountType.admin,
        )
        customer = make_customer(db_session)
        deal = make_deal(db_session, customer.id)
        log = make_activity_log(db_session, deal.id)

        response = client.put(
            f"/api/v1/deals/{deal.id}/activity-logs/{log.id}",
            json=build_activity_log_payload(),
        )

        assert response.status_code == 403

    def test_sales_forbidden_for_other_users_deal(
        self, client: TestClient, db_session: Session
    ) -> None:
        create_and_login_as(
            client,
            db_session,
            email="sales_update_activity_log_other@example.com",
            account_type=AccountType.sales,
        )
        other_sales_user = create_user(
            db_session, email="other_sales_owner_update_activity_log@example.com"
        )
        customer = make_customer(db_session, assigned_user_id=other_sales_user.id)
        deal = make_deal(db_session, customer.id)
        log = make_activity_log(db_session, deal.id)

        response = client.put(
            f"/api/v1/deals/{deal.id}/activity-logs/{log.id}",
            json=build_activity_log_payload(),
        )

        assert response.status_code == 403

    def test_fails_when_activity_log_not_found(
        self, client: TestClient, db_session: Session
    ) -> None:
        create_and_login_as(
            client,
            db_session,
            email="manager_update_activity_log_missing@example.com",
            account_type=AccountType.manager,
        )
        customer = make_customer(db_session)
        deal = make_deal(db_session, customer.id)

        response = client.put(
            f"/api/v1/deals/{deal.id}/activity-logs/{uuid.uuid4()}",
            json=build_activity_log_payload(),
        )

        assert response.status_code == 404

    def test_fails_when_deal_id_mismatch(self, client: TestClient, db_session: Session) -> None:
        create_and_login_as(
            client,
            db_session,
            email="manager_update_activity_log_mismatch@example.com",
            account_type=AccountType.manager,
        )
        customer = make_customer(db_session)
        deal = make_deal(db_session, customer.id)
        other_deal = make_deal(db_session, customer.id)
        log = make_activity_log(db_session, deal.id)

        response = client.put(
            f"/api/v1/deals/{other_deal.id}/activity-logs/{log.id}",
            json=build_activity_log_payload(),
        )

        assert response.status_code == 404

    def test_fails_when_not_logged_in(self, client: TestClient, db_session: Session) -> None:
        customer = make_customer(db_session)
        deal = make_deal(db_session, customer.id)
        log = make_activity_log(db_session, deal.id)

        response = client.put(
            f"/api/v1/deals/{deal.id}/activity-logs/{log.id}",
            json=build_activity_log_payload(),
        )

        assert response.status_code == 401

    def test_fails_when_required_field_missing(
        self, client: TestClient, db_session: Session
    ) -> None:
        create_and_login_as(
            client,
            db_session,
            email="manager_update_activity_log_missing_field@example.com",
            account_type=AccountType.manager,
        )
        customer = make_customer(db_session)
        deal = make_deal(db_session, customer.id)
        log = make_activity_log(db_session, deal.id)
        payload = build_activity_log_payload()
        del payload["type"]

        response = client.put(f"/api/v1/deals/{deal.id}/activity-logs/{log.id}", json=payload)

        assert response.status_code == 422

    def test_fails_when_type_is_invalid(self, client: TestClient, db_session: Session) -> None:
        create_and_login_as(
            client,
            db_session,
            email="manager_update_activity_log_invalid_type@example.com",
            account_type=AccountType.manager,
        )
        customer = make_customer(db_session)
        deal = make_deal(db_session, customer.id)
        log = make_activity_log(db_session, deal.id)

        response = client.put(
            f"/api/v1/deals/{deal.id}/activity-logs/{log.id}",
            json=build_activity_log_payload(type="invalid_type"),
        )

        assert response.status_code == 422

    def test_response_matches_request_fields(self, client: TestClient, db_session: Session) -> None:
        create_and_login_as(
            client,
            db_session,
            email="manager_update_activity_log_fields@example.com",
            account_type=AccountType.manager,
        )
        customer = make_customer(db_session)
        deal = make_deal(db_session, customer.id)
        log = make_activity_log(db_session, deal.id)
        payload = build_activity_log_payload(
            type="visit", activityDate="2026-07-01", note="訪問しました"
        )

        response = client.put(f"/api/v1/deals/{deal.id}/activity-logs/{log.id}", json=payload)

        assert response.status_code == 200
        body = response.json()
        assert body["activityLogId"] == log.id
        assert body["type"] == "visit"
        assert body["activityDate"] == "2026-07-01"
        assert body["note"] == "訪問しました"

    def test_note_can_be_updated_to_null(self, client: TestClient, db_session: Session) -> None:
        create_and_login_as(
            client,
            db_session,
            email="manager_update_activity_log_null_note@example.com",
            account_type=AccountType.manager,
        )
        customer = make_customer(db_session)
        deal = make_deal(db_session, customer.id)
        log = make_activity_log(db_session, deal.id, note="元のメモ")
        payload = build_activity_log_payload(note=None)

        response = client.put(f"/api/v1/deals/{deal.id}/activity-logs/{log.id}", json=payload)

        assert response.status_code == 200
        assert response.json()["note"] is None

    def test_persists_update(self, client: TestClient, db_session: Session) -> None:
        create_and_login_as(
            client,
            db_session,
            email="manager_update_activity_log_persist@example.com",
            account_type=AccountType.manager,
        )
        customer = make_customer(db_session)
        deal = make_deal(db_session, customer.id)
        log = make_activity_log(db_session, deal.id)

        response = client.put(
            f"/api/v1/deals/{deal.id}/activity-logs/{log.id}",
            json=build_activity_log_payload(note="更新後メモ"),
        )

        assert response.status_code == 200
        db_session.expire_all()
        persisted_log = db_session.get(ActivityLog, log.id)
        assert persisted_log is not None
        assert persisted_log.note == "更新後メモ"
