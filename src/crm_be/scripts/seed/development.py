import uuid

from datetime import date

from sqlalchemy.orm import Session

from crm_be.models.activity_log import ActivityLog
from crm_be.models.customer import Customer
from crm_be.models.deal import Deal
from crm_be.scripts.seed.sales_manager_users import seed_sales_manager_users
from crm_be.store.enums.activity_type import ActivityType
from crm_be.store.enums.deal_plan import DealPlan
from crm_be.store.enums.deal_status import DealStatus
from crm_be.store.enums.industry_type import IndustryType


def seed_development(db: Session) -> None:
    users = seed_sales_manager_users(db)
    if users is None:
        print("Development seed data already exists. Skipping.")
        return
    sales_user, manager_user = users

    customer_alpha = Customer(
        id=str(uuid.uuid4()),
        company_name="株式会社アルファ商事",
        industry=IndustryType.technology,
        company_size=250,
        contact_name="山田 一郎",
        phone="0312340001",
        email="yamada@alpha-shoji.example.com",
        assigned_user_id=sales_user.id,
    )
    customer_beta = Customer(
        id=str(uuid.uuid4()),
        company_name="ベータ物流株式会社",
        industry=IndustryType.manufacturing,
        company_size=80,
        contact_name="鈴木 二郎",
        phone="0312340002",
        email="suzuki@beta-logistics.example.com",
        assigned_user_id=sales_user.id,
    )
    customer_gamma = Customer(
        id=str(uuid.uuid4()),
        company_name="ガンマフーズ株式会社",
        industry=IndustryType.retail,
        company_size=30,
        contact_name="佐藤 三郎",
        phone="0312340003",
        email="sato@gamma-foods.example.com",
        assigned_user_id=manager_user.id,
    )
    db.add_all([customer_alpha, customer_beta, customer_gamma])
    db.flush()

    deal_alpha_1 = Deal(
        id=str(uuid.uuid4()),
        customer_id=customer_alpha.id,
        title="新規契約",
        status=DealStatus.negotiation,
        amount=1200000,
        plan=DealPlan.professional,
        license_count=20,
        contract_period=12,
    )
    deal_alpha_2 = Deal(
        id=str(uuid.uuid4()),
        customer_id=customer_alpha.id,
        title="追加ライセンス",
        status=DealStatus.closed_won,
        amount=300000,
        plan=DealPlan.professional,
        license_count=5,
        contract_period=12,
    )
    deal_alpha_3 = Deal(
        id=str(uuid.uuid4()),
        customer_id=customer_alpha.id,
        title="更新提案",
        status=DealStatus.lead,
        amount=600000,
        plan=DealPlan.starter,
        license_count=10,
        contract_period=6,
    )
    deal_beta_1 = Deal(
        id=str(uuid.uuid4()),
        customer_id=customer_beta.id,
        title="新規導入",
        status=DealStatus.proposal,
        amount=2400000,
        plan=DealPlan.enterprise,
        license_count=50,
        contract_period=24,
    )
    db.add_all([deal_alpha_1, deal_alpha_2, deal_alpha_3, deal_beta_1])
    db.flush()

    db.add_all(
        [
            ActivityLog(
                id=str(uuid.uuid4()),
                deal_id=deal_alpha_1.id,
                type=ActivityType.call,
                activity_date=date(2026, 6, 2),
                note="製品概要のヒアリングを実施。",
            ),
            ActivityLog(
                id=str(uuid.uuid4()),
                deal_id=deal_alpha_1.id,
                type=ActivityType.visit,
                activity_date=date(2026, 6, 10),
                note="先方オフィスに訪問し、デモンストレーションを実施。",
            ),
            ActivityLog(
                id=str(uuid.uuid4()),
                deal_id=deal_alpha_2.id,
                type=ActivityType.email,
                activity_date=date(2026, 6, 15),
                note="追加ライセンスの見積書を送付。",
            ),
            # deal_alpha_3 はログなしのdealとして作成
            ActivityLog(
                id=str(uuid.uuid4()),
                deal_id=deal_beta_1.id,
                type=ActivityType.online_meeting,
                activity_date=date(2026, 6, 5),
                note="オンラインで初回提案を実施。",
            ),
            ActivityLog(
                id=str(uuid.uuid4()),
                deal_id=deal_beta_1.id,
                type=ActivityType.call,
                activity_date=date(2026, 6, 20),
                note="提案内容について電話でフォローアップ。",
            ),
        ]
    )

    print("Development seed data inserted successfully.")
