import uuid

from unittest.mock import MagicMock

import pytest

from sqlalchemy.orm import Session

from crm_be.models.customer import Customer
from crm_be.models.deal import Deal
from crm_be.repositories.customer.repository import create_customer
from crm_be.repositories.deal.repository import (
    create_deal,
    get_deal_by_id,
    update_deal,
    update_deal_status,
)
from crm_be.store.enums.deal_plan import DealPlan
from crm_be.store.enums.deal_status import DealStatus
from crm_be.store.enums.industry_type import IndustryType
from tests.conftest import RollbackTracker


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


class TestCreateDeal:
    def test_persists_deal(self, db_session: Session) -> None:
        customer = create_customer(db_session, build_customer())
        deal = build_deal(customer.id)

        created_deal = create_deal(db_session, deal)

        db_session.expire_all()
        assert db_session.get(Deal, created_deal.id) is not None

    def test_returns_persisted_deal(self, db_session: Session) -> None:
        customer = create_customer(db_session, build_customer())
        deal = build_deal(
            customer.id,
            title="A社商談",
            status=DealStatus.lead,
            amount=5000,
            plan=DealPlan.enterprise,
            license_count=10,
            contract_period=24,
        )

        created_deal = create_deal(db_session, deal)

        assert created_deal.title == "A社商談"
        assert created_deal.status == DealStatus.lead
        assert created_deal.amount == 5000
        assert created_deal.plan == DealPlan.enterprise
        assert created_deal.license_count == 10
        assert created_deal.contract_period == 24

    def test_persists_customer_id(self, db_session: Session) -> None:
        customer = create_customer(db_session, build_customer())
        deal = build_deal(customer.id)

        created_deal = create_deal(db_session, deal)

        db_session.expire_all()
        persisted_deal = db_session.get(Deal, created_deal.id)
        assert persisted_deal is not None
        assert persisted_deal.customer_id == customer.id

    def test_rolls_back_on_commit_failure(
        self, db_session_commit_error: Session, rollback_tracker: RollbackTracker
    ) -> None:
        deal = build_deal(str(uuid.uuid4()))

        with pytest.raises(Exception, match="Simulated commit error"):
            create_deal(db_session_commit_error, deal)

        assert rollback_tracker.called is True


class TestGetDealById:
    def test_locks_deal_and_related_customer_rows_when_requested(self) -> None:
        session = MagicMock(spec=Session)
        session.scalars.return_value.one_or_none.return_value = None

        get_deal_by_id(session, str(uuid.uuid4()), for_update=True)

        stmt = session.scalars.call_args[0][0]
        assert "FOR UPDATE" in str(stmt)


class TestUpdateDeal:
    def test_persists_all_fields(self, db_session: Session) -> None:
        customer = create_customer(db_session, build_customer())
        deal = create_deal(db_session, build_deal(customer.id))

        update_deal(
            db_session,
            deal,
            title="A社商談",
            amount=5000,
            plan=DealPlan.enterprise,
            license_count=10,
            contract_period=24,
        )

        db_session.expire_all()
        persisted_deal = db_session.get(Deal, deal.id)
        assert persisted_deal is not None
        assert persisted_deal.title == "A社商談"
        assert persisted_deal.amount == 5000
        assert persisted_deal.plan == DealPlan.enterprise
        assert persisted_deal.license_count == 10
        assert persisted_deal.contract_period == 24

    def test_returns_updated_deal(self, db_session: Session) -> None:
        customer = create_customer(db_session, build_customer())
        deal = create_deal(db_session, build_deal(customer.id))

        updated_deal = update_deal(
            db_session,
            deal,
            title="A社商談",
            amount=5000,
            plan=DealPlan.enterprise,
            license_count=10,
            contract_period=24,
        )

        assert updated_deal.title == "A社商談"

    def test_rolls_back_on_commit_failure(
        self, db_session_commit_error: Session, rollback_tracker: RollbackTracker
    ) -> None:
        deal = build_deal(str(uuid.uuid4()))

        with pytest.raises(Exception, match="Simulated commit error"):
            update_deal(
                db_session_commit_error,
                deal,
                title="A社商談",
                amount=5000,
                plan=DealPlan.enterprise,
                license_count=10,
                contract_period=24,
            )

        assert rollback_tracker.called is True


class TestUpdateDealStatus:
    def test_persists_status(self, db_session: Session) -> None:
        customer = create_customer(db_session, build_customer())
        deal = create_deal(db_session, build_deal(customer.id))

        update_deal_status(db_session, deal, DealStatus.negotiation)

        db_session.expire_all()
        persisted_deal = db_session.get(Deal, deal.id)
        assert persisted_deal is not None
        assert persisted_deal.status == DealStatus.negotiation

    def test_returns_updated_deal(self, db_session: Session) -> None:
        customer = create_customer(db_session, build_customer())
        deal = create_deal(db_session, build_deal(customer.id))

        updated_deal = update_deal_status(db_session, deal, DealStatus.negotiation)

        assert updated_deal.status == DealStatus.negotiation

    def test_rolls_back_on_commit_failure(
        self, db_session_commit_error: Session, rollback_tracker: RollbackTracker
    ) -> None:
        deal = build_deal(str(uuid.uuid4()))

        with pytest.raises(Exception, match="Simulated commit error"):
            update_deal_status(db_session_commit_error, deal, DealStatus.negotiation)

        assert rollback_tracker.called is True
