import uuid

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest

from sqlalchemy.orm import Session

from crm_be.models.customer import Customer
from crm_be.models.deal import Deal
from crm_be.repositories.customer.repository import (
    assign_customer_user,
    create_customer,
    get_customer_by_id,
    get_customers,
    unassign_customer_user,
    update_customer,
)
from crm_be.store.enums.deal_plan import DealPlan
from crm_be.store.enums.deal_status import DealStatus
from crm_be.store.enums.industry_type import IndustryType
from tests.conftest import RollbackTracker
from tests.factories.user import create_user

# get_customersのpage_sizeはAPI層のクエリパラメータとして決定される値のため、
# repository自体はどんな値でも受け付ける。テストでは任意の固定値として扱う。
PAGE_SIZE = 10


def build_customer(**override: object) -> Customer:
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
    return Customer(**defaults)


def build_deal(customer_id: str, **override: object) -> Deal:
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
    return Deal(**defaults)


class TestCreateCustomer:
    def test_persists_customer(self, db_session: Session) -> None:
        customer = build_customer()

        created_customer = create_customer(db_session, customer)

        db_session.expire_all()
        assert db_session.get(Customer, created_customer.id) is not None

    def test_returns_persisted_customer(self, db_session: Session) -> None:
        customer = build_customer(company_name="山田商事")

        created_customer = create_customer(db_session, customer)

        assert created_customer.company_name == "山田商事"

    def test_persists_assigned_user_id(self, db_session: Session) -> None:
        sales_user = create_user(db_session)
        customer = build_customer(assigned_user_id=sales_user.id)

        created_customer = create_customer(db_session, customer)

        db_session.expire_all()
        persisted_customer = db_session.get(Customer, created_customer.id)
        assert persisted_customer is not None
        assert persisted_customer.assigned_user_id == sales_user.id

    def test_persists_null_assigned_user_id(self, db_session: Session) -> None:
        customer = build_customer(assigned_user_id=None)

        created_customer = create_customer(db_session, customer)

        db_session.expire_all()
        persisted_customer = db_session.get(Customer, created_customer.id)
        assert persisted_customer is not None
        assert persisted_customer.assigned_user_id is None

    def test_rolls_back_on_commit_failure(
        self, db_session_commit_error: Session, rollback_tracker: RollbackTracker
    ) -> None:
        customer = build_customer()

        with pytest.raises(Exception, match="Simulated commit error"):
            create_customer(db_session_commit_error, customer)

        assert rollback_tracker.called is True


class TestGetCustomers:
    def test_returns_all_customers_when_no_filter(self, db_session: Session) -> None:
        sales_user = create_user(db_session)
        own_customer = create_customer(db_session, build_customer(assigned_user_id=sales_user.id))
        other_sales_user = create_user(db_session)
        other_customer = create_customer(
            db_session, build_customer(assigned_user_id=other_sales_user.id)
        )
        unassigned_customer = create_customer(db_session, build_customer(assigned_user_id=None))

        result, total_count = get_customers(db_session, page_size=PAGE_SIZE)

        ids = {customer.id for customer in result}
        assert ids == {own_customer.id, other_customer.id, unassigned_customer.id}
        assert total_count == 3

    def test_includes_customers_assigned_to_given_user(self, db_session: Session) -> None:
        sales_user = create_user(db_session)
        own_customer = create_customer(db_session, build_customer(assigned_user_id=sales_user.id))

        result, _ = get_customers(db_session, visible_to_user_id=sales_user.id, page_size=PAGE_SIZE)

        assert own_customer.id in {customer.id for customer in result}

    def test_includes_unassigned_customers(self, db_session: Session) -> None:
        sales_user = create_user(db_session)
        unassigned_customer = create_customer(db_session, build_customer(assigned_user_id=None))

        result, _ = get_customers(db_session, visible_to_user_id=sales_user.id, page_size=PAGE_SIZE)

        assert unassigned_customer.id in {customer.id for customer in result}

    def test_excludes_customers_assigned_to_other_users(self, db_session: Session) -> None:
        sales_user = create_user(db_session)
        other_sales_user = create_user(db_session)
        other_customer = create_customer(
            db_session, build_customer(assigned_user_id=other_sales_user.id)
        )

        result, _ = get_customers(db_session, visible_to_user_id=sales_user.id, page_size=PAGE_SIZE)

        assert other_customer.id not in {customer.id for customer in result}

    def test_orders_by_created_at_descending(self, db_session: Session) -> None:
        now = datetime.now(UTC)
        older_customer = create_customer(
            db_session, build_customer(created_at=now - timedelta(days=1))
        )
        newer_customer = create_customer(db_session, build_customer(created_at=now))

        result, _ = get_customers(db_session, page_size=PAGE_SIZE)

        assert [customer.id for customer in result] == [newer_customer.id, older_customer.id]

    def test_orders_by_id_descending_when_created_at_is_same(self, db_session: Session) -> None:
        # created_atが同一の顧客を複数作成する。
        # created_atだけでは順序が不定になるため、idの降順がタイブレークとして
        # 使われることを確認する。
        now = datetime.now(UTC)
        customers = sorted(
            (create_customer(db_session, build_customer(created_at=now)) for _ in range(3)),
            key=lambda customer: customer.id,
            reverse=True,
        )

        result, _ = get_customers(db_session, page_size=PAGE_SIZE)

        assert [customer.id for customer in result] == [customer.id for customer in customers]

    def test_raises_value_error_when_page_is_zero(self, db_session: Session) -> None:
        # page=0はページ番号として不正なため、ValueErrorが送出されることを確認する。
        with pytest.raises(ValueError, match="page must be 1 or greater"):
            get_customers(db_session, page=0, page_size=PAGE_SIZE)

    def test_raises_value_error_when_page_is_negative(self, db_session: Session) -> None:
        # pageに負数を渡した場合も同様にValueErrorが送出されることを確認する。
        with pytest.raises(ValueError, match="page must be 1 or greater"):
            get_customers(db_session, page=-1, page_size=PAGE_SIZE)

    def test_raises_value_error_when_page_size_is_zero(self, db_session: Session) -> None:
        # page_size=0は1ページあたりの件数として不正なため、ValueErrorが送出されることを確認する。
        with pytest.raises(ValueError, match="page_size must be 1 or greater"):
            get_customers(db_session, page_size=0)

    def test_raises_value_error_when_page_size_is_negative(self, db_session: Session) -> None:
        # page_sizeに負数を渡した場合も同様にValueErrorが送出されることを確認する。
        with pytest.raises(ValueError, match="page_size must be 1 or greater"):
            get_customers(db_session, page_size=-1)

    def test_returns_empty_list_when_no_customers(self, db_session: Session) -> None:
        result, total_count = get_customers(db_session, page_size=PAGE_SIZE)

        assert result == []
        assert total_count == 0

    def test_loads_assigned_user(self, db_session: Session) -> None:
        sales_user = create_user(db_session)
        create_customer(db_session, build_customer(assigned_user_id=sales_user.id))

        result, _ = get_customers(db_session, page_size=PAGE_SIZE)

        assert result[0].assigned_user is not None
        assert result[0].assigned_user.id == sales_user.id

    def test_limits_results_to_page_size(self, db_session: Session) -> None:
        # 顧客を15件作成する（1ページあたりの件数10件を超える数）
        for _ in range(15):
            create_customer(db_session, build_customer())

        # page=1（1ページ目）を指定して取得する
        result, total_count = get_customers(db_session, page=1, page_size=PAGE_SIZE)

        # 1ページ目にはページサイズ分の10件しか含まれないこと
        assert len(result) == 10
        # 一方、全体の件数（total_count）は絞り込まれず15件のままであること
        assert total_count == 15

    def test_returns_remaining_items_on_second_page(self, db_session: Session) -> None:
        now = datetime.now(UTC)
        # created_atをずらしながら15件作成する。i分前で作成しているため、
        # customers[0]が最新、customers[14]が最も古い顧客になる
        # （get_customersはcreated_atの降順で返す仕様のため、この並び順が結果の並び順と対応する）
        customers = [
            create_customer(db_session, build_customer(created_at=now - timedelta(minutes=i)))
            for i in range(15)
        ]

        # page=2（2ページ目）を指定して取得する
        result, total_count = get_customers(db_session, page=2, page_size=PAGE_SIZE)

        # 全体件数は15件のまま
        assert total_count == 15
        # 2ページ目には、1ページ目（新しい順に10件）に入りきらなかった
        # 残り5件（11件目〜15件目＝customers[10:15]）が、同じ並び順で返ること
        assert [customer.id for customer in result] == [
            customer.id for customer in customers[10:15]
        ]


class TestGetCustomerById:
    def test_locks_customer_row_when_requested(self) -> None:
        session = MagicMock(spec=Session)
        session.scalars.return_value.one_or_none.return_value = None

        get_customer_by_id(session, str(uuid.uuid4()), for_update=True)

        stmt = session.scalars.call_args[0][0]
        assert "FOR UPDATE" in str(stmt)

    def test_returns_matching_customer(self, db_session: Session) -> None:
        customer = create_customer(db_session, build_customer())

        result = get_customer_by_id(db_session, customer.id)

        assert result is not None
        assert result.id == customer.id

    def test_returns_none_when_not_found(self, db_session: Session) -> None:
        result = get_customer_by_id(db_session, str(uuid.uuid4()))

        assert result is None

    def test_loads_assigned_user(self, db_session: Session) -> None:
        sales_user = create_user(db_session)
        customer = create_customer(db_session, build_customer(assigned_user_id=sales_user.id))

        result = get_customer_by_id(db_session, customer.id)

        assert result is not None
        assert result.assigned_user is not None
        assert result.assigned_user.id == sales_user.id

    def test_assigned_user_is_none_when_unassigned(self, db_session: Session) -> None:
        customer = create_customer(db_session, build_customer(assigned_user_id=None))

        result = get_customer_by_id(db_session, customer.id)

        assert result is not None
        assert result.assigned_user is None

    def test_loads_deals_ordered_by_created_at_descending(self, db_session: Session) -> None:
        customer = create_customer(db_session, build_customer())
        now = datetime.now(UTC)
        older_deal = build_deal(customer.id, created_at=now - timedelta(days=1))
        newer_deal = build_deal(customer.id, created_at=now)
        db_session.add_all([older_deal, newer_deal])
        db_session.commit()

        result = get_customer_by_id(db_session, customer.id)

        assert result is not None
        assert [deal.id for deal in result.deals] == [newer_deal.id, older_deal.id]

    def test_returns_empty_deals_when_none_exist(self, db_session: Session) -> None:
        customer = create_customer(db_session, build_customer())

        result = get_customer_by_id(db_session, customer.id)

        assert result is not None
        assert result.deals == []


class TestAssignCustomerUser:
    def test_assigns_given_user(self, db_session: Session) -> None:
        sales_user = create_user(db_session)
        customer = create_customer(db_session, build_customer(assigned_user_id=None))

        assign_customer_user(db_session, customer, sales_user.id)

        db_session.expire_all()
        persisted_customer = db_session.get(Customer, customer.id)
        assert persisted_customer is not None
        assert persisted_customer.assigned_user_id == sales_user.id

    def test_assigns_from_unassigned(self, db_session: Session) -> None:
        sales_user = create_user(db_session)
        customer = create_customer(db_session, build_customer(assigned_user_id=None))
        assert customer.assigned_user_id is None

        assign_customer_user(db_session, customer, sales_user.id)

        assert customer.assigned_user_id == sales_user.id

    def test_reassigning_to_same_user_is_idempotent(self, db_session: Session) -> None:
        sales_user = create_user(db_session)
        customer = create_customer(db_session, build_customer(assigned_user_id=sales_user.id))

        assign_customer_user(db_session, customer, sales_user.id)

        db_session.expire_all()
        persisted_customer = db_session.get(Customer, customer.id)
        assert persisted_customer is not None
        assert persisted_customer.assigned_user_id == sales_user.id

    def test_returns_updated_customer(self, db_session: Session) -> None:
        sales_user = create_user(db_session)
        customer = create_customer(db_session, build_customer(assigned_user_id=None))

        updated_customer = assign_customer_user(db_session, customer, sales_user.id)

        assert updated_customer.assigned_user_id == sales_user.id

    def test_rolls_back_on_commit_failure(
        self, db_session_commit_error: Session, rollback_tracker: RollbackTracker
    ) -> None:
        customer = build_customer(assigned_user_id=None)

        with pytest.raises(Exception, match="Simulated commit error"):
            assign_customer_user(db_session_commit_error, customer, str(uuid.uuid4()))

        assert rollback_tracker.called is True


class TestUnassignCustomerUser:
    def test_unassigns_customer(self, db_session: Session) -> None:
        sales_user = create_user(db_session)
        customer = create_customer(db_session, build_customer(assigned_user_id=sales_user.id))

        unassign_customer_user(db_session, customer)

        db_session.expire_all()
        persisted_customer = db_session.get(Customer, customer.id)
        assert persisted_customer is not None
        assert persisted_customer.assigned_user_id is None

    def test_unassigning_already_unassigned_is_idempotent(self, db_session: Session) -> None:
        customer = create_customer(db_session, build_customer(assigned_user_id=None))

        unassign_customer_user(db_session, customer)

        db_session.expire_all()
        persisted_customer = db_session.get(Customer, customer.id)
        assert persisted_customer is not None
        assert persisted_customer.assigned_user_id is None

    def test_returns_updated_customer(self, db_session: Session) -> None:
        sales_user = create_user(db_session)
        customer = create_customer(db_session, build_customer(assigned_user_id=sales_user.id))

        updated_customer = unassign_customer_user(db_session, customer)

        assert updated_customer.assigned_user_id is None

    def test_rolls_back_on_commit_failure(
        self, db_session_commit_error: Session, rollback_tracker: RollbackTracker
    ) -> None:
        customer = build_customer(assigned_user_id=str(uuid.uuid4()))

        with pytest.raises(Exception, match="Simulated commit error"):
            unassign_customer_user(db_session_commit_error, customer)

        assert rollback_tracker.called is True


class TestUpdateCustomer:
    def test_updates_all_fields(self, db_session: Session) -> None:
        customer = create_customer(db_session, build_customer())

        update_customer(
            db_session,
            customer,
            company_name="更新後株式会社",
            industry=IndustryType.finance,
            company_size=200,
            contact_name="鈴木一郎",
            phone="06-1111-2222",
            email="updated@example.com",
        )

        db_session.expire_all()
        persisted_customer = db_session.get(Customer, customer.id)
        assert persisted_customer is not None
        assert persisted_customer.company_name == "更新後株式会社"
        assert persisted_customer.industry == IndustryType.finance
        assert persisted_customer.company_size == 200
        assert persisted_customer.contact_name == "鈴木一郎"
        assert persisted_customer.phone == "06-1111-2222"
        assert persisted_customer.email == "updated@example.com"

    def test_returns_updated_customer(self, db_session: Session) -> None:
        customer = create_customer(db_session, build_customer())

        updated_customer = update_customer(
            db_session,
            customer,
            company_name="更新後株式会社",
            industry=IndustryType.finance,
            company_size=200,
            contact_name="鈴木一郎",
            phone="06-1111-2222",
            email="updated2@example.com",
        )

        assert updated_customer.company_name == "更新後株式会社"

    def test_does_not_change_assigned_user_id(self, db_session: Session) -> None:
        sales_user = create_user(db_session)
        customer = create_customer(db_session, build_customer(assigned_user_id=sales_user.id))

        update_customer(
            db_session,
            customer,
            company_name="更新後株式会社",
            industry=IndustryType.finance,
            company_size=200,
            contact_name="鈴木一郎",
            phone="06-1111-2222",
            email="updated3@example.com",
        )

        db_session.expire_all()
        persisted_customer = db_session.get(Customer, customer.id)
        assert persisted_customer is not None
        assert persisted_customer.assigned_user_id == sales_user.id

    def test_rolls_back_on_commit_failure(
        self, db_session_commit_error: Session, rollback_tracker: RollbackTracker
    ) -> None:
        customer = build_customer()

        with pytest.raises(Exception, match="Simulated commit error"):
            update_customer(
                db_session_commit_error,
                customer,
                company_name="更新後株式会社",
                industry=IndustryType.finance,
                company_size=200,
                contact_name="鈴木一郎",
                phone="06-1111-2222",
                email="updated4@example.com",
            )

        assert rollback_tracker.called is True
