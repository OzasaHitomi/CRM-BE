import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from crm_be.logic.security.jwt import create_access_token
from crm_be.models.user import User
from crm_be.store.constants.auth import ACCESS_TOKEN_COOKIE_KEY
from tests.factories.user import create_user


def create_access_token_cookie(client: TestClient, user: User) -> None:
    access_token = create_access_token(uuid.UUID(user.id), user.account_type, user.name)
    # ログイン経由で発行されたCookieと同じdomainで保持させることで、
    # ログアウトのdelete_cookie()による削除が正しく反映されるようにする。
    client.cookies.set(ACCESS_TOKEN_COOKIE_KEY, access_token, domain=client.base_url.host)


def create_and_login_as(client: TestClient, db: Session, **override: object) -> User:
    user = create_user(db, **override)
    create_access_token_cookie(client, user)
    return user
