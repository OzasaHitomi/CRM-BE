from collections.abc import Generator

from sqlalchemy.orm import Session

from crm_be.core.config.database import SessionLocal


def get_db() -> Generator[Session]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
