import os

from collections.abc import Generator
from dataclasses import dataclass
from pathlib import Path

import pytest

from alembic import command
from alembic.config import Config
from dotenv import load_dotenv
from sqlalchemy import Connection, create_engine
from sqlalchemy.orm import Session, sessionmaker

load_dotenv(".env.test.unit")

# pytestはホストマシン(Docker外)からdbコンテナに接続するため、
# ホストに公開されたポート(MYSQL_HOST_PORT)から明示的に組み立てる。
os.environ["MYSQL_HOST"] = "127.0.0.1"
os.environ["MYSQL_PORT"] = os.environ["MYSQL_HOST_PORT"]

from crm_be.core.config.base import core_settings  # noqa: E402, I001


@pytest.fixture(scope="session", autouse=True)
def apply_migrations() -> Generator[None]:
    """pytest開始時にテストDBへAlembicマイグレーションを適用する"""

    # プロジェクトルートを基準に alembic.ini を取得
    project_root = Path(__file__).resolve().parents[1]
    alembic_dir = project_root / "src" / "crm_be"

    alembic_ini_path = alembic_dir / "alembic.ini"

    # alembic.ini を絶対パスで読み込む
    alembic_cfg = Config(str(alembic_ini_path))

    # 動的に sqlalchemy.url をテスト用に書き換える
    db_url = core_settings.database_url
    alembic_cfg.set_main_option("sqlalchemy.url", db_url)

    # 最新の head までアップグレード
    command.upgrade(alembic_cfg, "head")

    yield


@pytest.fixture
def db_connection() -> Generator[Connection]:
    database_url = core_settings.database_url
    engine = create_engine(database_url, echo=False)
    connection = engine.connect()
    transaction = connection.begin()
    try:
        yield connection
    finally:
        if transaction.is_active:
            transaction.rollback()
        connection.close()


# 正常系のDBセッション
@pytest.fixture
def db_session(db_connection: Connection) -> Generator[Session]:
    testing_session = sessionmaker(bind=db_connection)
    session = testing_session()
    try:
        yield session
    finally:
        session.close()


@dataclass
class RollbackTracker:
    called: bool = False


@pytest.fixture
def rollback_tracker() -> RollbackTracker:
    return RollbackTracker()


# コミット時に例外を発生させるDBセッション
@pytest.fixture
def db_session_commit_error(
    db_connection: Connection,
    rollback_tracker: RollbackTracker,
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[Session]:
    testing_session = sessionmaker(bind=db_connection)
    session = testing_session()
    original_rollback = session.rollback

    def fake_commit() -> None:
        raise Exception("Simulated commit error")

    def fake_rollback() -> None:
        rollback_tracker.called = True
        return original_rollback()

    monkeypatch.setattr(session, "commit", fake_commit)
    monkeypatch.setattr(session, "rollback", fake_rollback)

    try:
        yield session
    finally:
        session.close()
