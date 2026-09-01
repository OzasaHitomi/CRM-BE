import uuid

from typing import Annotated

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from crm_be.api.common.dependencies.authentication import verify_access_token
from crm_be.api.common.dependencies.database import get_db
from crm_be.core.config.base import core_settings
from crm_be.exceptions.forbidden_exception import ForbiddenException
from crm_be.exceptions.unauthorized_exception import UnauthorizedException
from crm_be.logic.security.jwt import create_access_token
from crm_be.logic.security.password import verify_password
from crm_be.logic.security.types import AccessTokenPayload
from crm_be.repositories.user.repository import get_user_by_email
from crm_be.schemas.v1.request.auth import LoginRequest
from crm_be.schemas.v1.response.auth import MeResponse
from crm_be.store.constants.auth import ACCESS_TOKEN_COOKIE_KEY

router = APIRouter()


@router.get("/me", response_model=MeResponse)
def me(
    access_token_payload: Annotated[AccessTokenPayload, Depends(verify_access_token)],
) -> MeResponse:
    return MeResponse(
        user_id=access_token_payload.sub,
        role=access_token_payload.role,
        name=access_token_payload.name,
    )


@router.post("/login", status_code=204)
def login(
    body: LoginRequest,
    response: Response,
    session: Annotated[Session, Depends(get_db)],
) -> None:
    email = body.email
    password = body.password

    user = get_user_by_email(session, email)
    if user is None or not verify_password(password, user.hashed_password):
        raise UnauthorizedException("メールアドレスまたはパスワードが正しくありません")

    if not user.is_active:
        raise ForbiddenException("ユーザーが停止されています")

    access_token = create_access_token(uuid.UUID(user.id), user.account_type, user.name)

    response.set_cookie(
        key=ACCESS_TOKEN_COOKIE_KEY,
        value=access_token,
        httponly=True,
        samesite="lax",
        secure=core_settings.cookie_secure,
    )


@router.post("/logout", status_code=204)
def logout(response: Response) -> None:
    response.delete_cookie(
        key=ACCESS_TOKEN_COOKIE_KEY,
        httponly=True,
        samesite="lax",
        secure=core_settings.cookie_secure,
    )
