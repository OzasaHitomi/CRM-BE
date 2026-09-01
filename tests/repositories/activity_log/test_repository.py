import uuid

from datetime import date

import pytest

from sqlalchemy.orm import Session

from crm_be.models.activity_log import ActivityLog
from crm_be.models.customer import Customer
from crm_be.models.deal import Deal
from crm_be.repositories.activity_log.repository import (
    create_activity_log,
    get_activity_log_by_id,
    update_activity_log,
)
from crm_be.repositories.customer.repository import create_customer
from crm_be.repositories.deal.repository import create_deal
from crm_be.store.enums.activity_type import ActivityType
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


def build_activity_log(deal_id: str, **override: object) -> ActivityLog:
    defaults: dict[str, object] = {
        "id": str(uuid.uuid4()),
        "deal_id": deal_id,
        "type": ActivityType.call,
        "activity_date": date.today(),
        "note": "架電しました",
    }
    defaults.update(override)
    return ActivityLog(**defaults)


class TestCreateActivityLog:
    def test_persists_activity_log(self, db_session: Session) -> None:
        customer = create_customer(db_session, build_customer())
        deal = create_deal(db_session, build_deal(customer.id))
        activity_log = build_activity_log(deal.id)

        created_activity_log = create_activity_log(db_session, activity_log)

        db_session.expire_all()
        assert db_session.get(ActivityLog, created_activity_log.id) is not None

    def test_returns_persisted_activity_log(self, db_session: Session) -> None:
        customer = create_customer(db_session, build_customer())
        deal = create_deal(db_session, build_deal(customer.id))
        activity_log = build_activity_log(
            deal.id,
            type=ActivityType.visit,
            activity_date=date(2026, 7, 1),
            note="訪問しました",
        )

        created_activity_log = create_activity_log(db_session, activity_log)

        assert created_activity_log.type == ActivityType.visit
        assert created_activity_log.activity_date == date(2026, 7, 1)
        assert created_activity_log.note == "訪問しました"

    def test_persists_null_note(self, db_session: Session) -> None:
        customer = create_customer(db_session, build_customer())
        deal = create_deal(db_session, build_deal(customer.id))
        activity_log = build_activity_log(deal.id, note=None)

        created_activity_log = create_activity_log(db_session, activity_log)

        db_session.expire_all()
        persisted_activity_log = db_session.get(ActivityLog, created_activity_log.id)
        assert persisted_activity_log is not None
        assert persisted_activity_log.note is None

    def test_rolls_back_on_commit_failure(
        self, db_session_commit_error: Session, rollback_tracker: RollbackTracker
    ) -> None:
        activity_log = build_activity_log(str(uuid.uuid4()))

        with pytest.raises(Exception, match="Simulated commit error"):
            create_activity_log(db_session_commit_error, activity_log)

        assert rollback_tracker.called is True


class TestGetActivityLogById:
    def test_returns_matching_activity_log(self, db_session: Session) -> None:
        customer = create_customer(db_session, build_customer())
        deal = create_deal(db_session, build_deal(customer.id))
        activity_log = create_activity_log(db_session, build_activity_log(deal.id))

        result = get_activity_log_by_id(db_session, activity_log.id)

        assert result is not None
        assert result.id == activity_log.id

    def test_returns_none_when_not_found(self, db_session: Session) -> None:
        result = get_activity_log_by_id(db_session, str(uuid.uuid4()))

        assert result is None

    def test_loads_deal_and_customer(self, db_session: Session) -> None:
        customer = create_customer(db_session, build_customer())
        deal = create_deal(db_session, build_deal(customer.id))
        activity_log = create_activity_log(db_session, build_activity_log(deal.id))

        result = get_activity_log_by_id(db_session, activity_log.id)

        assert result is not None
        assert result.deal.id == deal.id
        assert result.deal.customer.id == customer.id


class TestUpdateActivityLog:
    def test_persists_fields(self, db_session: Session) -> None:
        customer = create_customer(db_session, build_customer())
        deal = create_deal(db_session, build_deal(customer.id))
        activity_log = create_activity_log(db_session, build_activity_log(deal.id))

        update_activity_log(
            db_session,
            activity_log,
            type=ActivityType.visit,
            activity_date=date(2026, 7, 1),
            note="訪問しました",
        )

        db_session.expire_all()
        persisted_activity_log = db_session.get(ActivityLog, activity_log.id)
        assert persisted_activity_log is not None
        assert persisted_activity_log.type == ActivityType.visit
        assert persisted_activity_log.activity_date == date(2026, 7, 1)
        assert persisted_activity_log.note == "訪問しました"

    def test_returns_updated_activity_log(self, db_session: Session) -> None:
        customer = create_customer(db_session, build_customer())
        deal = create_deal(db_session, build_deal(customer.id))
        activity_log = create_activity_log(db_session, build_activity_log(deal.id))

        updated_activity_log = update_activity_log(
            db_session,
            activity_log,
            type=ActivityType.visit,
            activity_date=date(2026, 7, 1),
            note="訪問しました",
        )

        assert updated_activity_log.type == ActivityType.visit

    def test_can_update_note_to_none(self, db_session: Session) -> None:
        customer = create_customer(db_session, build_customer())
        deal = create_deal(db_session, build_deal(customer.id))
        activity_log = create_activity_log(db_session, build_activity_log(deal.id))

        update_activity_log(
            db_session,
            activity_log,
            type=ActivityType.call,
            activity_date=date.today(),
            note=None,
        )

        db_session.expire_all()
        persisted_activity_log = db_session.get(ActivityLog, activity_log.id)
        assert persisted_activity_log is not None
        assert persisted_activity_log.note is None

    def test_rolls_back_on_commit_failure(
        self, db_session_commit_error: Session, rollback_tracker: RollbackTracker
    ) -> None:
        activity_log = build_activity_log(str(uuid.uuid4()))

        with pytest.raises(Exception, match="Simulated commit error"):
            update_activity_log(
                db_session_commit_error,
                activity_log,
                type=ActivityType.visit,
                activity_date=date(2026, 7, 1),
                note="訪問しました",
            )

        assert rollback_tracker.called is True
