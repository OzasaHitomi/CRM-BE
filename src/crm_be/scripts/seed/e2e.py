from sqlalchemy.orm import Session

from crm_be.scripts.seed.sales_manager_users import seed_sales_manager_users


def seed_e2e(db: Session) -> None:
    """E2Eテスト用に、adminに加えてsales/managerユーザーのみを用意する。
    顧客・商談・活動ログは各テストがAPI/UI経由で用意する前提のため、ここでは作成しない。
    """
    users = seed_sales_manager_users(db)
    if users is None:
        print("E2E seed data already exists. Skipping.")
        return

    print("E2E seed data (users only) inserted successfully.")
