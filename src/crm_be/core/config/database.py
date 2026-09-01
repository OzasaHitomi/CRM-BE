from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from crm_be.core.config.base import core_settings

engine = create_engine(core_settings.database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
