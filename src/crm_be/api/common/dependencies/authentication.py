from typing import Annotated

from fastapi import Cookie, Depends
from jwt import ExpiredSignatureError, InvalidTokenError
from sqlalchemy.orm import Session

from crm_be.api.common.dependencies.database import get_db
from crm_be.exceptions.unauthorized_exception import UnauthorizedException
from crm_be.logic.security.jwt import verify_jwt_token
from crm_be.logic.security.types import AccessTokenPayload
from crm_be.models.user import User
from crm_be.repositories.user.repository import get_user_by_id


def verify_access_token(
    access_token: str | None = Cookie(default=None),
) -> AccessTokenPayload:
    if access_token is None:
        raise UnauthorizedException("access_tokenが存在しません")

    try:
        decoded_token = verify_jwt_token(access_token)
    except ExpiredSignatureError as e:
        raise UnauthorizedException("トークンの有効期限が切れています") from e
    except InvalidTokenError as e:
        raise UnauthorizedException("無効なトークンです") from e

    # if decoded_token.type != "access":
    #     raise UnauthorizedException("access_tokenのタイプが不正です")

    return decoded_token


def get_current_user(
    access_token_payload: Annotated[AccessTokenPayload, Depends(verify_access_token)],
    session: Annotated[Session, Depends(get_db)],
) -> User:
    target_user = get_user_by_id(session, access_token_payload.sub)
    if target_user is None:
        raise UnauthorizedException("ユーザーが見つかりません")

    if target_user.is_active is False:
        raise UnauthorizedException("ユーザーが非アクティブです")

    return target_user
