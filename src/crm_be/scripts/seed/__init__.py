from crm_be.core.config.base import core_settings
from crm_be.core.config.database import SessionLocal
from crm_be.scripts.seed.admin import seed_admin
from crm_be.scripts.seed.development import seed_development
from crm_be.scripts.seed.e2e import seed_e2e


def main() -> None:
    if core_settings.environment == "production":
        print("ENVIRONMENT=production のため、シード処理をスキップします。")
        return

    db = SessionLocal()
    try:
        seed_admin(db)
        if core_settings.seed_profile == "development":
            seed_development(db)
        elif core_settings.seed_profile == "e2e":
            seed_e2e(db)
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    main()
