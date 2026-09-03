import uuid

from datetime import UTC, date, datetime, timedelta

import pytest

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
from tests.conftest import RollbackTracker
from tests.factories.auth import create_and_login_as
from tests.factories.user import create_user


def build_customer_payload(**override: object) -> dict:
    defaults: dict[str, object] = {
        "companyName": "テスト株式会社",
        "industry": "technology",
        "companySize": 100,
        "contactName": "山田太郎",
        "phone": "03-1234-5678",
        "email": f"customer_{uuid.uuid4().hex[:8]}@example.com",
    }
    defaults.update(override)
    return defaults


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


def build_deal_payload(**override: object) -> dict:
    defaults: dict[str, object] = {
        "title": "商談",
        "amount": 1000,
        "plan": "starter",
        "licenseCount": 1,
        "contractPeriod": 12,
    }
    defaults.update(override)
    return defaults


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


class TestCreateCustomer:
    @pytest.mark.parametrize(
        ("field", "value"),
        [
            ("companyName", "a" * 101),
            ("companySize", 0),
            ("companySize", 2_147_483_648),
            ("contactName", "a" * 101),
            ("phone", "0" * 21),
            ("email", f"{'a' * 244}@example.com"),
        ],
    )
    def test_rejects_values_outside_database_constraints(
        self,
        field: str,
        value: object,
        client: TestClient,
        db_session: Session,
    ) -> None:
        create_and_login_as(
            client,
            db_session,
            email=f"validation_{field}_{uuid.uuid4().hex[:8]}@example.com",
            account_type=AccountType.sales,
        )

        response = client.post(
            "/api/v1/customers",
            json=build_customer_payload(**{field: value}),
        )

        assert response.status_code == 422

    def test_assigns_caller_when_sales(self, client: TestClient, db_session: Session) -> None:
        sales_user = create_and_login_as(
            client,
            db_session,
            email="sales_create_customer@example.com",
            account_type=AccountType.sales,
        )

        response = client.post("/api/v1/customers", json=build_customer_payload())

        assert response.status_code == 201
        body = response.json()
        assert body["assignedUser"] == {"userId": sales_user.id, "name": sales_user.name}

    def test_does_not_assign_when_manager(self, client: TestClient, db_session: Session) -> None:
        create_and_login_as(
            client,
            db_session,
            email="manager_create_customer@example.com",
            account_type=AccountType.manager,
        )

        response = client.post("/api/v1/customers", json=build_customer_payload())

        assert response.status_code == 201
        assert response.json()["assignedUser"] is None

    def test_fails_when_admin(self, client: TestClient, db_session: Session) -> None:
        create_and_login_as(
            client,
            db_session,
            email="admin_create_customer@example.com",
            account_type=AccountType.admin,
        )

        response = client.post("/api/v1/customers", json=build_customer_payload())

        assert response.status_code == 403

    def test_response_matches_request_fields(self, client: TestClient, db_session: Session) -> None:
        create_and_login_as(
            client,
            db_session,
            email="admin_response_fields@example.com",
            account_type=AccountType.sales,
        )
        payload = build_customer_payload(
            companyName="山田商事",
            industry="finance",
            companySize=50,
            contactName="鈴木一郎",
            phone="06-9876-5432",
            email="response_fields@example.com",
        )

        response = client.post("/api/v1/customers", json=payload)

        assert response.status_code == 201
        body = response.json()
        assert body["companyName"] == "山田商事"
        assert body["industry"] == "finance"
        assert body["companySize"] == 50
        assert body["contactName"] == "鈴木一郎"
        assert body["phone"] == "06-9876-5432"
        assert body["email"] == "response_fields@example.com"

    def test_persists_customer(self, client: TestClient, db_session: Session) -> None:
        create_and_login_as(
            client,
            db_session,
            email="admin_persist_customer@example.com",
            account_type=AccountType.sales,
        )

        response = client.post(
            "/api/v1/customers", json=build_customer_payload(companyName="山田商事")
        )

        customer_id = response.json()["customerId"]
        db_session.expire_all()
        persisted_customer = db_session.get(Customer, customer_id)
        assert persisted_customer is not None
        assert persisted_customer.company_name == "山田商事"

    def test_allows_duplicate_email(self, client: TestClient, db_session: Session) -> None:
        create_and_login_as(
            client,
            db_session,
            email="admin_duplicate_customer@example.com",
            account_type=AccountType.sales,
        )
        payload = build_customer_payload(email="duplicate_customer@example.com")

        first_response = client.post("/api/v1/customers", json=payload)
        second_response = client.post("/api/v1/customers", json=payload)

        assert first_response.status_code == 201
        assert second_response.status_code == 201

    def test_fails_when_not_logged_in(self, client: TestClient) -> None:
        response = client.post("/api/v1/customers", json=build_customer_payload())

        assert response.status_code == 401

    def test_fails_when_industry_is_invalid(self, client: TestClient, db_session: Session) -> None:
        create_and_login_as(
            client,
            db_session,
            email="admin_invalid_industry@example.com",
            account_type=AccountType.sales,
        )

        response = client.post(
            "/api/v1/customers", json=build_customer_payload(industry="invalid_industry")
        )

        assert response.status_code == 422

    def test_fails_when_email_is_invalid_format(
        self, client: TestClient, db_session: Session
    ) -> None:
        create_and_login_as(
            client,
            db_session,
            email="admin_invalid_email@example.com",
            account_type=AccountType.sales,
        )

        response = client.post(
            "/api/v1/customers", json=build_customer_payload(email="not-an-email")
        )

        assert response.status_code == 422

    def test_fails_when_required_field_missing(
        self, client: TestClient, db_session: Session
    ) -> None:
        create_and_login_as(
            client,
            db_session,
            email="admin_missing_field@example.com",
            account_type=AccountType.sales,
        )
        payload = build_customer_payload()
        del payload["companyName"]

        response = client.post("/api/v1/customers", json=payload)

        assert response.status_code == 422

    def test_returns_500_and_rolls_back_when_commit_fails(
        self,
        client_with_commit_error: TestClient,
        db_session: Session,
        rollback_tracker: RollbackTracker,
    ) -> None:
        create_and_login_as(
            client_with_commit_error,
            db_session,
            email="admin_commit_error@example.com",
            account_type=AccountType.sales,
        )

        response = client_with_commit_error.post("/api/v1/customers", json=build_customer_payload())

        assert response.status_code == 500
        assert response.json() == {"detail": "システムエラーが発生しました。"}
        assert rollback_tracker.called is True


class TestGetCustomers:
    def test_sales_sees_own_customer(self, client: TestClient, db_session: Session) -> None:
        sales_user = create_and_login_as(
            client, db_session, email="sales_get_own@example.com", account_type=AccountType.sales
        )
        own_customer = make_customer(db_session, assigned_user_id=sales_user.id)

        response = client.get("/api/v1/customers")

        assert response.status_code == 200
        ids = {item["customerId"] for item in response.json()["customers"]}
        assert own_customer.id in ids

    def test_sales_sees_unassigned_customer(self, client: TestClient, db_session: Session) -> None:
        create_and_login_as(
            client,
            db_session,
            email="sales_get_unassigned@example.com",
            account_type=AccountType.sales,
        )
        unassigned_customer = make_customer(db_session, assigned_user_id=None)

        response = client.get("/api/v1/customers")

        assert response.status_code == 200
        ids = {item["customerId"] for item in response.json()["customers"]}
        assert unassigned_customer.id in ids

    def test_sales_does_not_see_other_users_customer(
        self, client: TestClient, db_session: Session
    ) -> None:
        create_and_login_as(
            client,
            db_session,
            email="sales_get_excluded@example.com",
            account_type=AccountType.sales,
        )
        other_sales_user = create_user(db_session, email="other_sales_get@example.com")
        other_customer = make_customer(db_session, assigned_user_id=other_sales_user.id)

        response = client.get("/api/v1/customers")

        assert response.status_code == 200
        ids = {item["customerId"] for item in response.json()["customers"]}
        assert other_customer.id not in ids

    def test_manager_sees_all_customers(self, client: TestClient, db_session: Session) -> None:
        create_and_login_as(
            client,
            db_session,
            email="manager_get_all@example.com",
            account_type=AccountType.manager,
        )
        sales_user = create_user(db_session, email="sales_for_manager_get@example.com")
        assigned_customer = make_customer(db_session, assigned_user_id=sales_user.id)
        unassigned_customer = make_customer(db_session, assigned_user_id=None)

        response = client.get("/api/v1/customers")

        assert response.status_code == 200
        ids = {item["customerId"] for item in response.json()["customers"]}
        assert assigned_customer.id in ids
        assert unassigned_customer.id in ids

    def test_admin_sees_all_customers(self, client: TestClient, db_session: Session) -> None:
        create_and_login_as(
            client, db_session, email="admin_get_all@example.com", account_type=AccountType.admin
        )
        sales_user = create_user(db_session, email="sales_for_admin_get@example.com")
        assigned_customer = make_customer(db_session, assigned_user_id=sales_user.id)
        unassigned_customer = make_customer(db_session, assigned_user_id=None)

        response = client.get("/api/v1/customers")

        assert response.status_code == 200
        ids = {item["customerId"] for item in response.json()["customers"]}
        assert assigned_customer.id in ids
        assert unassigned_customer.id in ids

    def test_response_fields_match_customer(self, client: TestClient, db_session: Session) -> None:
        create_and_login_as(
            client, db_session, email="admin_get_fields@example.com", account_type=AccountType.admin
        )
        customer = make_customer(
            db_session,
            company_name="山田商事",
            industry=IndustryType.finance,
        )

        response = client.get("/api/v1/customers")

        item = next(i for i in response.json()["customers"] if i["customerId"] == customer.id)
        assert item["companyName"] == "山田商事"
        assert item["industry"] == "finance"

    def test_includes_nested_assigned_user_when_assigned(
        self, client: TestClient, db_session: Session
    ) -> None:
        create_and_login_as(
            client, db_session, email="admin_get_nested@example.com", account_type=AccountType.admin
        )
        sales_user = create_user(db_session, email="sales_for_nested_get@example.com")
        customer = make_customer(db_session, assigned_user_id=sales_user.id)

        response = client.get("/api/v1/customers")

        item = next(i for i in response.json()["customers"] if i["customerId"] == customer.id)
        assert item["assignedUser"] == {"userId": sales_user.id, "name": sales_user.name}

    def test_assigned_user_is_null_when_unassigned(
        self, client: TestClient, db_session: Session
    ) -> None:
        create_and_login_as(
            client, db_session, email="admin_get_null@example.com", account_type=AccountType.admin
        )
        customer = make_customer(db_session, assigned_user_id=None)

        response = client.get("/api/v1/customers")

        item = next(i for i in response.json()["customers"] if i["customerId"] == customer.id)
        assert item["assignedUser"] is None

    def test_fails_when_not_logged_in(self, client: TestClient) -> None:
        response = client.get("/api/v1/customers")

        assert response.status_code == 401

    def test_returns_empty_list_when_no_customers(
        self, client: TestClient, db_session: Session
    ) -> None:
        create_and_login_as(
            client, db_session, email="admin_get_empty@example.com", account_type=AccountType.admin
        )

        response = client.get("/api/v1/customers")

        assert response.status_code == 200
        body = response.json()
        assert body["customers"] == []
        # 顧客が0件のときも、ページネーション情報（現在ページ・1ページの件数・
        # 全件数・総ページ数）が正しい初期値で返ってくることを確認する
        assert body["pagination"] == {
            "page": 1,
            "pageSize": 10,
            "totalCount": 0,
            "totalPages": 0,
        }

    def test_defaults_to_first_page_with_ten_items(
        self, client: TestClient, db_session: Session
    ) -> None:
        # ページ指定なしでアクセスした場合、デフォルトで1ページ目・
        # 1ページあたり10件が返ることを確認するテスト
        create_and_login_as(
            client,
            db_session,
            email="admin_get_default_page@example.com",
            account_type=AccountType.admin,
        )
        for _ in range(11):
            make_customer(db_session)

        response = client.get("/api/v1/customers")

        body = response.json()
        # 11件の顧客を作成しても、1ページ目には10件までしか含まれない
        assert len(body["customers"]) == 10
        # 全件数は11件、ページサイズ10件なら総ページ数は2ページになる
        assert body["pagination"] == {
            "page": 1,
            "pageSize": 10,
            "totalCount": 11,
            "totalPages": 2,
        }

    def test_returns_remaining_items_on_second_page(
        self, client: TestClient, db_session: Session
    ) -> None:
        # 2ページ目をクエリパラメータで指定した場合、
        # 1ページ目に入りきらなかった残りの顧客が返ることを確認するテスト
        create_and_login_as(
            client,
            db_session,
            email="admin_get_second_page@example.com",
            account_type=AccountType.admin,
        )
        for _ in range(11):
            make_customer(db_session)

        response = client.get("/api/v1/customers", params={"page": 2})

        body = response.json()
        # 11件中10件は1ページ目に入るため、2ページ目には残り1件だけが返る
        assert len(body["customers"]) == 1
        assert body["pagination"]["page"] == 2

    def test_different_pages_return_different_customers(
        self, client: TestClient, db_session: Session
    ) -> None:
        # 1ページ目と2ページ目で取得できる顧客が重複していないことを確認するテスト
        create_and_login_as(
            client,
            db_session,
            email="admin_get_page_distinct@example.com",
            account_type=AccountType.admin,
        )
        for _ in range(11):
            make_customer(db_session)

        first_page = client.get("/api/v1/customers", params={"page": 1}).json()
        second_page = client.get("/api/v1/customers", params={"page": 2}).json()

        first_page_ids = {item["customerId"] for item in first_page["customers"]}
        second_page_ids = {item["customerId"] for item in second_page["customers"]}
        # isdisjoint()は2つの集合に共通する要素が1つもないことを確認するメソッド
        assert first_page_ids.isdisjoint(second_page_ids)

    def test_rejects_page_below_one(self, client: TestClient, db_session: Session) -> None:
        # pageに0のような不正な値（1未満）を指定した場合、
        # バリデーションエラー（422）になることを確認するテスト
        create_and_login_as(
            client,
            db_session,
            email="admin_get_invalid_page@example.com",
            account_type=AccountType.admin,
        )

        response = client.get("/api/v1/customers", params={"page": 0})

        assert response.status_code == 422

    def test_applies_custom_page_size(self, client: TestClient, db_session: Session) -> None:
        # pageSizeをクエリパラメータで指定した場合、その件数に絞り込まれ、
        # レスポンスのpagination.pageSizeにも反映されることを確認するテスト
        create_and_login_as(
            client,
            db_session,
            email="admin_get_custom_page_size@example.com",
            account_type=AccountType.admin,
        )
        for _ in range(5):
            make_customer(db_session)

        response = client.get("/api/v1/customers", params={"pageSize": 3})

        body = response.json()
        assert len(body["customers"]) == 3
        assert body["pagination"] == {
            "page": 1,
            "pageSize": 3,
            "totalCount": 5,
            "totalPages": 2,
        }

    def test_rejects_page_size_below_one(self, client: TestClient, db_session: Session) -> None:
        # pageSizeに0のような不正な値（1未満）を指定した場合、
        # バリデーションエラー（422）になることを確認するテスト
        create_and_login_as(
            client,
            db_session,
            email="admin_get_invalid_page_size_low@example.com",
            account_type=AccountType.admin,
        )

        response = client.get("/api/v1/customers", params={"pageSize": 0})

        assert response.status_code == 422

    def test_rejects_page_size_above_upper_limit(
        self, client: TestClient, db_session: Session
    ) -> None:
        # pageSizeの上限（100）を超える値を指定した場合、
        # バリデーションエラー（422）になることを確認するテスト
        create_and_login_as(
            client,
            db_session,
            email="admin_get_invalid_page_size_high@example.com",
            account_type=AccountType.admin,
        )

        response = client.get("/api/v1/customers", params={"pageSize": 101})

        assert response.status_code == 422


class TestGetCustomer:
    def test_manager_can_view_unassigned_customer(
        self, client: TestClient, db_session: Session
    ) -> None:
        create_and_login_as(
            client,
            db_session,
            email="manager_get_detail_unassigned@example.com",
            account_type=AccountType.manager,
        )
        customer = make_customer(db_session, assigned_user_id=None)

        response = client.get(f"/api/v1/customers/{customer.id}")

        assert response.status_code == 200
        assert response.json()["customerId"] == customer.id

    def test_manager_can_view_other_users_customer(
        self, client: TestClient, db_session: Session
    ) -> None:
        create_and_login_as(
            client,
            db_session,
            email="manager_get_detail_other@example.com",
            account_type=AccountType.manager,
        )
        sales_user = create_user(db_session, email="sales_owner_for_manager_detail@example.com")
        customer = make_customer(db_session, assigned_user_id=sales_user.id)

        response = client.get(f"/api/v1/customers/{customer.id}")

        assert response.status_code == 200
        assert response.json()["assignedUser"] == {"userId": sales_user.id, "name": sales_user.name}

    def test_admin_can_view_any_customer(self, client: TestClient, db_session: Session) -> None:
        create_and_login_as(
            client, db_session, email="admin_get_detail@example.com", account_type=AccountType.admin
        )
        customer = make_customer(db_session, assigned_user_id=None)

        response = client.get(f"/api/v1/customers/{customer.id}")

        assert response.status_code == 200

    def test_sales_can_view_own_customer(self, client: TestClient, db_session: Session) -> None:
        sales_user = create_and_login_as(
            client,
            db_session,
            email="sales_get_detail_own@example.com",
            account_type=AccountType.sales,
        )
        customer = make_customer(db_session, assigned_user_id=sales_user.id)

        response = client.get(f"/api/v1/customers/{customer.id}")

        assert response.status_code == 200

    def test_sales_forbidden_for_unassigned_customer(
        self, client: TestClient, db_session: Session
    ) -> None:
        create_and_login_as(
            client,
            db_session,
            email="sales_get_detail_unassigned@example.com",
            account_type=AccountType.sales,
        )
        customer = make_customer(db_session, assigned_user_id=None)

        response = client.get(f"/api/v1/customers/{customer.id}")

        assert response.status_code == 403

    def test_sales_forbidden_for_other_users_customer(
        self, client: TestClient, db_session: Session
    ) -> None:
        create_and_login_as(
            client,
            db_session,
            email="sales_get_detail_other@example.com",
            account_type=AccountType.sales,
        )
        other_sales_user = create_user(db_session, email="other_sales_owner_detail@example.com")
        customer = make_customer(db_session, assigned_user_id=other_sales_user.id)

        response = client.get(f"/api/v1/customers/{customer.id}")

        assert response.status_code == 403

    def test_fails_when_customer_not_found(self, client: TestClient, db_session: Session) -> None:
        create_and_login_as(
            client,
            db_session,
            email="manager_get_detail_missing@example.com",
            account_type=AccountType.manager,
        )

        response = client.get(f"/api/v1/customers/{uuid.uuid4()}")

        assert response.status_code == 404

    def test_fails_when_not_logged_in(self, client: TestClient, db_session: Session) -> None:
        customer = make_customer(db_session)

        response = client.get(f"/api/v1/customers/{customer.id}")

        assert response.status_code == 401

    def test_response_fields_match_customer(self, client: TestClient, db_session: Session) -> None:
        create_and_login_as(
            client,
            db_session,
            email="admin_get_detail_fields@example.com",
            account_type=AccountType.admin,
        )
        customer = make_customer(
            db_session, company_name="山田商事", industry=IndustryType.finance, company_size=42
        )

        response = client.get(f"/api/v1/customers/{customer.id}")

        body = response.json()
        assert body["companyName"] == "山田商事"
        assert body["industry"] == "finance"
        assert body["companySize"] == 42

    def test_includes_nested_deal_with_fields(
        self, client: TestClient, db_session: Session
    ) -> None:
        create_and_login_as(
            client,
            db_session,
            email="admin_get_detail_deal@example.com",
            account_type=AccountType.admin,
        )
        customer = make_customer(db_session)
        deal = make_deal(
            db_session,
            customer.id,
            title="A社商談",
            status=DealStatus.negotiation,
            amount=5000,
            plan=DealPlan.enterprise,
            license_count=10,
            contract_period=24,
        )

        response = client.get(f"/api/v1/customers/{customer.id}")

        assert response.status_code == 200
        deals = response.json()["deals"]
        assert len(deals) == 1
        assert deals[0]["dealId"] == deal.id
        assert deals[0]["title"] == "A社商談"
        assert deals[0]["status"] == "negotiation"
        assert deals[0]["amount"] == 5000
        assert deals[0]["plan"] == "enterprise"
        assert deals[0]["licenseCount"] == 10
        assert deals[0]["contractPeriod"] == 24
        assert deals[0]["activityLogs"] == []

    def test_returns_empty_deals_when_none_exist(
        self, client: TestClient, db_session: Session
    ) -> None:
        create_and_login_as(
            client,
            db_session,
            email="admin_get_detail_no_deals@example.com",
            account_type=AccountType.admin,
        )
        customer = make_customer(db_session)

        response = client.get(f"/api/v1/customers/{customer.id}")

        assert response.status_code == 200
        assert response.json()["deals"] == []

    def test_deals_ordered_by_created_at_descending(
        self, client: TestClient, db_session: Session
    ) -> None:
        create_and_login_as(
            client,
            db_session,
            email="admin_get_detail_order@example.com",
            account_type=AccountType.admin,
        )
        customer = make_customer(db_session)
        now = datetime.now(UTC)
        older_deal = make_deal(db_session, customer.id, created_at=now - timedelta(days=1))
        newer_deal = make_deal(db_session, customer.id, created_at=now)

        response = client.get(f"/api/v1/customers/{customer.id}")

        deal_ids = [d["dealId"] for d in response.json()["deals"]]
        assert deal_ids == [newer_deal.id, older_deal.id]

    def test_includes_nested_activity_logs_with_fields(
        self, client: TestClient, db_session: Session
    ) -> None:
        create_and_login_as(
            client,
            db_session,
            email="admin_get_detail_activity_log@example.com",
            account_type=AccountType.admin,
        )
        customer = make_customer(db_session)
        deal = make_deal(db_session, customer.id)
        log = make_activity_log(
            db_session,
            deal.id,
            type=ActivityType.visit,
            activity_date=date(2026, 7, 1),
            note="訪問しました",
        )

        response = client.get(f"/api/v1/customers/{customer.id}")

        activity_logs = response.json()["deals"][0]["activityLogs"]
        assert len(activity_logs) == 1
        assert activity_logs[0]["activityLogId"] == log.id
        assert activity_logs[0]["type"] == "visit"
        assert activity_logs[0]["activityDate"] == "2026-07-01"
        assert activity_logs[0]["note"] == "訪問しました"


class TestAssignCustomerUser:
    def test_sales_can_assign_unassigned_customer(
        self, client: TestClient, db_session: Session
    ) -> None:
        sales_user = create_and_login_as(
            client,
            db_session,
            email="sales_assign_unassigned@example.com",
            account_type=AccountType.sales,
        )
        customer = make_customer(db_session, assigned_user_id=None)

        response = client.put(f"/api/v1/customers/{customer.id}/assigned-user")

        assert response.status_code == 200
        body = response.json()
        assert body["customerId"] == customer.id
        assert body["assignedUser"] == {"userId": sales_user.id, "name": sales_user.name}

    def test_manager_can_assign_unassigned_customer(
        self, client: TestClient, db_session: Session
    ) -> None:
        manager_user = create_and_login_as(
            client,
            db_session,
            email="manager_assign_unassigned@example.com",
            account_type=AccountType.manager,
        )
        customer = make_customer(db_session, assigned_user_id=None)

        response = client.put(f"/api/v1/customers/{customer.id}/assigned-user")

        assert response.status_code == 200
        assert response.json()["assignedUser"]["userId"] == manager_user.id

    def test_reassigning_to_self_is_idempotent(
        self, client: TestClient, db_session: Session
    ) -> None:
        sales_user = create_and_login_as(
            client,
            db_session,
            email="sales_assign_self@example.com",
            account_type=AccountType.sales,
        )
        customer = make_customer(db_session, assigned_user_id=sales_user.id)

        response = client.put(f"/api/v1/customers/{customer.id}/assigned-user")

        assert response.status_code == 200

    def test_fails_when_admin(self, client: TestClient, db_session: Session) -> None:
        create_and_login_as(
            client,
            db_session,
            email="admin_assign_forbidden@example.com",
            account_type=AccountType.admin,
        )
        customer = make_customer(db_session, assigned_user_id=None)

        response = client.put(f"/api/v1/customers/{customer.id}/assigned-user")

        assert response.status_code == 403

    def test_fails_when_assigned_to_other_user(
        self, client: TestClient, db_session: Session
    ) -> None:
        create_and_login_as(
            client,
            db_session,
            email="sales_assign_blocked@example.com",
            account_type=AccountType.sales,
        )
        other_sales_user = create_user(db_session, email="other_sales_assign_owner@example.com")
        customer = make_customer(db_session, assigned_user_id=other_sales_user.id)

        response = client.put(f"/api/v1/customers/{customer.id}/assigned-user")

        assert response.status_code == 403
        db_session.expire_all()
        persisted_customer = db_session.get(Customer, customer.id)
        assert persisted_customer is not None
        assert persisted_customer.assigned_user_id == other_sales_user.id

    def test_fails_when_customer_not_found(self, client: TestClient, db_session: Session) -> None:
        create_and_login_as(
            client,
            db_session,
            email="sales_assign_missing@example.com",
            account_type=AccountType.sales,
        )

        response = client.put(f"/api/v1/customers/{uuid.uuid4()}/assigned-user")

        assert response.status_code == 404

    def test_fails_when_not_logged_in(self, client: TestClient, db_session: Session) -> None:
        customer = make_customer(db_session)

        response = client.put(f"/api/v1/customers/{customer.id}/assigned-user")

        assert response.status_code == 401

    def test_persists_assignment(self, client: TestClient, db_session: Session) -> None:
        sales_user = create_and_login_as(
            client,
            db_session,
            email="sales_assign_persist@example.com",
            account_type=AccountType.sales,
        )
        customer = make_customer(db_session, assigned_user_id=None)

        client.put(f"/api/v1/customers/{customer.id}/assigned-user")

        db_session.expire_all()
        persisted_customer = db_session.get(Customer, customer.id)
        assert persisted_customer is not None
        assert persisted_customer.assigned_user_id == sales_user.id


class TestUnassignCustomerUser:
    def test_sales_can_unassign_own_customer(self, client: TestClient, db_session: Session) -> None:
        sales_user = create_and_login_as(
            client,
            db_session,
            email="sales_unassign_own@example.com",
            account_type=AccountType.sales,
        )
        customer = make_customer(db_session, assigned_user_id=sales_user.id)

        response = client.delete(f"/api/v1/customers/{customer.id}/assigned-user")

        assert response.status_code == 204

    def test_sales_idempotent_when_already_unassigned(
        self, client: TestClient, db_session: Session
    ) -> None:
        create_and_login_as(
            client,
            db_session,
            email="sales_unassign_noop@example.com",
            account_type=AccountType.sales,
        )
        customer = make_customer(db_session, assigned_user_id=None)

        response = client.delete(f"/api/v1/customers/{customer.id}/assigned-user")

        assert response.status_code == 204

    def test_manager_can_unassign_other_users_customer(
        self, client: TestClient, db_session: Session
    ) -> None:
        create_and_login_as(
            client,
            db_session,
            email="manager_unassign_other@example.com",
            account_type=AccountType.manager,
        )
        sales_user = create_user(db_session, email="sales_owner_for_manager_unassign@example.com")
        customer = make_customer(db_session, assigned_user_id=sales_user.id)

        response = client.delete(f"/api/v1/customers/{customer.id}/assigned-user")

        assert response.status_code == 204

    def test_admin_can_unassign_other_users_customer(
        self, client: TestClient, db_session: Session
    ) -> None:
        create_and_login_as(
            client,
            db_session,
            email="admin_unassign_other@example.com",
            account_type=AccountType.admin,
        )
        sales_user = create_user(db_session, email="sales_owner_for_admin_unassign@example.com")
        customer = make_customer(db_session, assigned_user_id=sales_user.id)

        response = client.delete(f"/api/v1/customers/{customer.id}/assigned-user")

        assert response.status_code == 204

    def test_sales_fails_when_assigned_to_other_user(
        self, client: TestClient, db_session: Session
    ) -> None:
        create_and_login_as(
            client,
            db_session,
            email="sales_unassign_blocked@example.com",
            account_type=AccountType.sales,
        )
        other_sales_user = create_user(db_session, email="other_sales_unassign_owner@example.com")
        customer = make_customer(db_session, assigned_user_id=other_sales_user.id)

        response = client.delete(f"/api/v1/customers/{customer.id}/assigned-user")

        assert response.status_code == 403
        db_session.expire_all()
        persisted_customer = db_session.get(Customer, customer.id)
        assert persisted_customer is not None
        assert persisted_customer.assigned_user_id == other_sales_user.id

    def test_fails_when_customer_not_found(self, client: TestClient, db_session: Session) -> None:
        create_and_login_as(
            client,
            db_session,
            email="sales_unassign_missing@example.com",
            account_type=AccountType.sales,
        )

        response = client.delete(f"/api/v1/customers/{uuid.uuid4()}/assigned-user")

        assert response.status_code == 404

    def test_fails_when_not_logged_in(self, client: TestClient, db_session: Session) -> None:
        customer = make_customer(db_session)

        response = client.delete(f"/api/v1/customers/{customer.id}/assigned-user")

        assert response.status_code == 401

    def test_persists_unassignment(self, client: TestClient, db_session: Session) -> None:
        sales_user = create_and_login_as(
            client,
            db_session,
            email="sales_unassign_persist@example.com",
            account_type=AccountType.sales,
        )
        customer = make_customer(db_session, assigned_user_id=sales_user.id)

        client.delete(f"/api/v1/customers/{customer.id}/assigned-user")

        db_session.expire_all()
        persisted_customer = db_session.get(Customer, customer.id)
        assert persisted_customer is not None
        assert persisted_customer.assigned_user_id is None


class TestCreateDeal:
    @pytest.mark.parametrize(
        ("field", "value"),
        [
            ("title", "a" * 101),
            ("amount", 0),
            ("amount", 2_147_483_648),
            ("licenseCount", 0),
            ("contractPeriod", 0),
        ],
    )
    def test_rejects_values_outside_database_constraints(
        self,
        field: str,
        value: object,
        client: TestClient,
        db_session: Session,
    ) -> None:
        create_and_login_as(
            client,
            db_session,
            email=f"deal_validation_{field}_{uuid.uuid4().hex[:8]}@example.com",
            account_type=AccountType.manager,
        )
        customer = make_customer(db_session)

        response = client.post(
            f"/api/v1/customers/{customer.id}/deals",
            json=build_deal_payload(**{field: value}),
        )

        assert response.status_code == 422

    def test_sales_can_create_for_own_customer(
        self, client: TestClient, db_session: Session
    ) -> None:
        sales_user = create_and_login_as(
            client,
            db_session,
            email="sales_create_deal_own@example.com",
            account_type=AccountType.sales,
        )
        customer = make_customer(db_session, assigned_user_id=sales_user.id)

        response = client.post(f"/api/v1/customers/{customer.id}/deals", json=build_deal_payload())

        assert response.status_code == 201

    def test_sales_forbidden_for_unassigned_customer(
        self, client: TestClient, db_session: Session
    ) -> None:
        create_and_login_as(
            client,
            db_session,
            email="sales_create_deal_unassigned@example.com",
            account_type=AccountType.sales,
        )
        customer = make_customer(db_session, assigned_user_id=None)

        response = client.post(f"/api/v1/customers/{customer.id}/deals", json=build_deal_payload())

        assert response.status_code == 403

    def test_sales_forbidden_for_other_users_customer(
        self, client: TestClient, db_session: Session
    ) -> None:
        create_and_login_as(
            client,
            db_session,
            email="sales_create_deal_other@example.com",
            account_type=AccountType.sales,
        )
        other_sales_user = create_user(db_session, email="other_sales_create_deal@example.com")
        customer = make_customer(db_session, assigned_user_id=other_sales_user.id)

        response = client.post(f"/api/v1/customers/{customer.id}/deals", json=build_deal_payload())

        assert response.status_code == 403

    def test_manager_can_create_for_other_users_customer(
        self, client: TestClient, db_session: Session
    ) -> None:
        create_and_login_as(
            client,
            db_session,
            email="manager_create_deal_other@example.com",
            account_type=AccountType.manager,
        )
        sales_user = create_user(
            db_session, email="sales_owner_for_manager_create_deal@example.com"
        )
        customer = make_customer(db_session, assigned_user_id=sales_user.id)

        response = client.post(f"/api/v1/customers/{customer.id}/deals", json=build_deal_payload())

        assert response.status_code == 201

    def test_fails_when_admin(self, client: TestClient, db_session: Session) -> None:
        create_and_login_as(
            client,
            db_session,
            email="admin_create_deal_forbidden@example.com",
            account_type=AccountType.admin,
        )
        customer = make_customer(db_session)

        response = client.post(f"/api/v1/customers/{customer.id}/deals", json=build_deal_payload())

        assert response.status_code == 403

    def test_fails_when_customer_not_found(self, client: TestClient, db_session: Session) -> None:
        create_and_login_as(
            client,
            db_session,
            email="manager_create_deal_missing@example.com",
            account_type=AccountType.manager,
        )

        response = client.post(f"/api/v1/customers/{uuid.uuid4()}/deals", json=build_deal_payload())

        assert response.status_code == 404

    def test_fails_when_not_logged_in(self, client: TestClient, db_session: Session) -> None:
        customer = make_customer(db_session)

        response = client.post(f"/api/v1/customers/{customer.id}/deals", json=build_deal_payload())

        assert response.status_code == 401

    def test_role_check_precedes_customer_lookup_for_admin(
        self, client: TestClient, db_session: Session
    ) -> None:
        create_and_login_as(
            client,
            db_session,
            email="admin_create_deal_missing@example.com",
            account_type=AccountType.admin,
        )

        response = client.post(f"/api/v1/customers/{uuid.uuid4()}/deals", json=build_deal_payload())

        assert response.status_code == 403

    def test_customer_lookup_runs_after_role_check_for_sales(
        self, client: TestClient, db_session: Session
    ) -> None:
        create_and_login_as(
            client,
            db_session,
            email="sales_create_deal_missing@example.com",
            account_type=AccountType.sales,
        )

        response = client.post(f"/api/v1/customers/{uuid.uuid4()}/deals", json=build_deal_payload())

        assert response.status_code == 404

    def test_status_is_always_lead(self, client: TestClient, db_session: Session) -> None:
        create_and_login_as(
            client,
            db_session,
            email="manager_create_deal_status@example.com",
            account_type=AccountType.manager,
        )
        customer = make_customer(db_session)

        response = client.post(f"/api/v1/customers/{customer.id}/deals", json=build_deal_payload())

        assert response.status_code == 201
        assert response.json()["status"] == "lead"

    def test_response_matches_request_fields(self, client: TestClient, db_session: Session) -> None:
        create_and_login_as(
            client,
            db_session,
            email="manager_create_deal_fields@example.com",
            account_type=AccountType.manager,
        )
        customer = make_customer(db_session)
        payload = build_deal_payload(
            title="A社商談",
            amount=5000,
            plan="enterprise",
            licenseCount=10,
            contractPeriod=24,
        )

        response = client.post(f"/api/v1/customers/{customer.id}/deals", json=payload)

        assert response.status_code == 201
        body = response.json()
        assert body["title"] == "A社商談"
        assert body["amount"] == 5000
        assert body["plan"] == "enterprise"
        assert body["licenseCount"] == 10
        assert body["contractPeriod"] == 24

    def test_activity_logs_is_empty_on_creation(
        self, client: TestClient, db_session: Session
    ) -> None:
        create_and_login_as(
            client,
            db_session,
            email="manager_create_deal_logs@example.com",
            account_type=AccountType.manager,
        )
        customer = make_customer(db_session)

        response = client.post(f"/api/v1/customers/{customer.id}/deals", json=build_deal_payload())

        assert response.json()["activityLogs"] == []

    def test_persists_deal(self, client: TestClient, db_session: Session) -> None:
        create_and_login_as(
            client,
            db_session,
            email="manager_create_deal_persist@example.com",
            account_type=AccountType.manager,
        )
        customer = make_customer(db_session)

        response = client.post(
            f"/api/v1/customers/{customer.id}/deals",
            json=build_deal_payload(title="A社商談"),
        )

        deal_id = response.json()["dealId"]
        db_session.expire_all()
        persisted_deal = db_session.get(Deal, deal_id)
        assert persisted_deal is not None
        assert persisted_deal.title == "A社商談"
        assert persisted_deal.customer_id == customer.id

    def test_fails_when_required_field_missing(
        self, client: TestClient, db_session: Session
    ) -> None:
        create_and_login_as(
            client,
            db_session,
            email="manager_create_deal_missing_field@example.com",
            account_type=AccountType.manager,
        )
        customer = make_customer(db_session)
        payload = build_deal_payload()
        del payload["title"]

        response = client.post(f"/api/v1/customers/{customer.id}/deals", json=payload)

        assert response.status_code == 422

    def test_fails_when_plan_is_invalid(self, client: TestClient, db_session: Session) -> None:
        create_and_login_as(
            client,
            db_session,
            email="manager_create_deal_invalid_plan@example.com",
            account_type=AccountType.manager,
        )
        customer = make_customer(db_session)

        response = client.post(
            f"/api/v1/customers/{customer.id}/deals",
            json=build_deal_payload(plan="invalid_plan"),
        )

        assert response.status_code == 422


def build_update_customer_payload(**override: object) -> dict:
    defaults: dict[str, object] = {
        "companyName": "更新後株式会社",
        "industry": "finance",
        "companySize": 200,
        "contactName": "鈴木一郎",
        "phone": "06-1111-2222",
        "email": f"updated_{uuid.uuid4().hex[:8]}@example.com",
    }
    defaults.update(override)
    return defaults


class TestUpdateCustomer:
    def test_sales_can_update_own_customer(self, client: TestClient, db_session: Session) -> None:
        sales_user = create_and_login_as(
            client,
            db_session,
            email="sales_update_own@example.com",
            account_type=AccountType.sales,
        )
        customer = make_customer(db_session, assigned_user_id=sales_user.id)

        response = client.put(
            f"/api/v1/customers/{customer.id}", json=build_update_customer_payload()
        )

        assert response.status_code == 200

    def test_manager_can_update_other_users_customer(
        self, client: TestClient, db_session: Session
    ) -> None:
        create_and_login_as(
            client,
            db_session,
            email="manager_update_other@example.com",
            account_type=AccountType.manager,
        )
        sales_user = create_user(db_session, email="sales_owner_for_manager_update@example.com")
        customer = make_customer(db_session, assigned_user_id=sales_user.id)

        response = client.put(
            f"/api/v1/customers/{customer.id}", json=build_update_customer_payload()
        )

        assert response.status_code == 200

    def test_fails_when_admin(self, client: TestClient, db_session: Session) -> None:
        create_and_login_as(
            client,
            db_session,
            email="admin_update_forbidden@example.com",
            account_type=AccountType.admin,
        )
        customer = make_customer(db_session)

        response = client.put(
            f"/api/v1/customers/{customer.id}", json=build_update_customer_payload()
        )

        assert response.status_code == 403

    def test_fails_when_unassigned_for_sales(self, client: TestClient, db_session: Session) -> None:
        create_and_login_as(
            client,
            db_session,
            email="sales_update_unassigned@example.com",
            account_type=AccountType.sales,
        )
        customer = make_customer(db_session, assigned_user_id=None)

        response = client.put(
            f"/api/v1/customers/{customer.id}", json=build_update_customer_payload()
        )

        assert response.status_code == 403

    def test_fails_when_assigned_to_other_user(
        self, client: TestClient, db_session: Session
    ) -> None:
        create_and_login_as(
            client,
            db_session,
            email="sales_update_blocked@example.com",
            account_type=AccountType.sales,
        )
        other_sales_user = create_user(db_session, email="other_sales_update_owner@example.com")
        customer = make_customer(
            db_session, assigned_user_id=other_sales_user.id, company_name="元の名前"
        )

        response = client.put(
            f"/api/v1/customers/{customer.id}", json=build_update_customer_payload()
        )

        assert response.status_code == 403
        db_session.expire_all()
        persisted_customer = db_session.get(Customer, customer.id)
        assert persisted_customer is not None
        assert persisted_customer.company_name == "元の名前"

    def test_fails_when_customer_not_found(self, client: TestClient, db_session: Session) -> None:
        create_and_login_as(
            client,
            db_session,
            email="manager_update_missing@example.com",
            account_type=AccountType.manager,
        )

        response = client.put(
            f"/api/v1/customers/{uuid.uuid4()}", json=build_update_customer_payload()
        )

        assert response.status_code == 404

    def test_fails_when_not_logged_in(self, client: TestClient, db_session: Session) -> None:
        customer = make_customer(db_session)

        response = client.put(
            f"/api/v1/customers/{customer.id}", json=build_update_customer_payload()
        )

        assert response.status_code == 401

    def test_response_fields_match_update(self, client: TestClient, db_session: Session) -> None:
        create_and_login_as(
            client,
            db_session,
            email="manager_update_fields@example.com",
            account_type=AccountType.manager,
        )
        customer = make_customer(db_session)

        response = client.put(
            f"/api/v1/customers/{customer.id}",
            json=build_update_customer_payload(
                companyName="更新後商事",
                industry="finance",
                companySize=300,
                contactName="佐藤花子",
                phone="03-9999-8888",
                email="response_check@example.com",
            ),
        )

        body = response.json()
        assert body["companyName"] == "更新後商事"
        assert body["industry"] == "finance"
        assert body["companySize"] == 300
        assert body["contactName"] == "佐藤花子"
        assert body["phone"] == "03-9999-8888"
        assert body["email"] == "response_check@example.com"

    def test_assigned_user_unchanged_in_response(
        self, client: TestClient, db_session: Session
    ) -> None:
        sales_user = create_and_login_as(
            client,
            db_session,
            email="sales_update_keeps_assigned_user@example.com",
            account_type=AccountType.sales,
        )
        customer = make_customer(db_session, assigned_user_id=sales_user.id)

        response = client.put(
            f"/api/v1/customers/{customer.id}", json=build_update_customer_payload()
        )

        assert response.json()["assignedUser"] == {
            "userId": sales_user.id,
            "name": sales_user.name,
        }

    def test_persists_update(self, client: TestClient, db_session: Session) -> None:
        create_and_login_as(
            client,
            db_session,
            email="manager_update_persist@example.com",
            account_type=AccountType.manager,
        )
        customer = make_customer(db_session)

        client.put(
            f"/api/v1/customers/{customer.id}",
            json=build_update_customer_payload(companyName="永続化テスト株式会社"),
        )

        db_session.expire_all()
        persisted_customer = db_session.get(Customer, customer.id)
        assert persisted_customer is not None
        assert persisted_customer.company_name == "永続化テスト株式会社"
