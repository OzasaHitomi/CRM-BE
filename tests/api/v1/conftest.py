from collections.abc import Generator

import pytest

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from crm_be.api.common.dependencies.database import get_db
from crm_be.main import app


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient]:
    def override_get_db() -> Generator[Session]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    # base_urlはドットを含むホスト名にする(cookiejarのeff_request_hostは
    # ドットなしホストに`.local`を付与するため、ドット入りにして単純なdomain一致にする)
    client = TestClient(app, base_url="http://testserver.example")
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def client_with_commit_error(
    db_session_commit_error: Session,
) -> Generator[TestClient]:
    def override_get_db() -> Generator[Session]:
        yield db_session_commit_error

    app.dependency_overrides[get_db] = override_get_db

    # base_urlはドットを含むホスト名にする(cookiejarのeff_request_hostは
    # ドットなしホストに`.local`を付与するため、ドット入りにして単純なdomain一致にする)
    client = TestClient(app, base_url="http://testserver.example", raise_server_exceptions=False)

    try:
        yield client
    finally:
        app.dependency_overrides.clear()
