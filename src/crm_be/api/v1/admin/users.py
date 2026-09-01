import uuid

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from crm_be.api.common.dependencies.authorization import user_checker
from crm_be.api.common.dependencies.database import get_db
from crm_be.exceptions.business_exception import BusinessException
from crm_be.exceptions.not_found_exception import NotFoundException
from crm_be.logic.security.password import hash_password
from crm_be.models.user import User
from crm_be.repositories.user.repository import (
    create_user as create_user_in_db,
    get_user_by_email,
    get_user_by_id,
    get_users_by_account_types,
    update_user_status as update_user_status_in_db,
)
from crm_be.schemas.v1.request.admin.user import CreateUserRequest, UpdateUserStatusRequest
from crm_be.schemas.v1.response.admin.user import (
    CreateUserResponse,
    GetUsersResponseItem,
    UpdateUserStatusResponse,
)
from crm_be.store.enums.account_type import AccountType

router = APIRouter()

NON_ADMIN_ACCOUNT_TYPES = [
    account_type for account_type in AccountType if account_type != AccountType.admin
]


@router.get(
    "",
    response_model=list[GetUsersResponseItem],
    dependencies=[Depends(user_checker({AccountType.admin}))],
)
def get_users(session: Annotated[Session, Depends(get_db)]) -> list[GetUsersResponseItem]:
    users = get_users_by_account_types(session, NON_ADMIN_ACCOUNT_TYPES)

    return [
        GetUsersResponseItem(
            user_id=uuid.UUID(user.id),
            name=user.name,
            email=user.email,
            role=user.account_type,
            is_active=user.is_active,
        )
        for user in users
    ]


@router.post(
    "",
    status_code=201,
    response_model=CreateUserResponse,
    dependencies=[Depends(user_checker({AccountType.admin}))],
)
def create_user(
    body: CreateUserRequest, session: Annotated[Session, Depends(get_db)]
) -> CreateUserResponse:
    if body.role == AccountType.admin:
        raise BusinessException("管理者ロールのユーザーはこのAPIから作成できません")

    if get_user_by_email(session, body.email) is not None:
        raise BusinessException("このメールアドレスは既に登録されています")

    user = User(
        name=body.name,
        email=body.email,
        hashed_password=hash_password(body.password),
        account_type=body.role,
    )
    created_user = create_user_in_db(session, user)

    return CreateUserResponse(
        user_id=uuid.UUID(created_user.id),
        name=created_user.name,
        email=created_user.email,
        role=created_user.account_type,
    )


@router.put(
    "/status/{user_id}",
    response_model=UpdateUserStatusResponse,
    dependencies=[Depends(user_checker({AccountType.admin}))],
)
def update_user_status(
    user_id: uuid.UUID,
    body: UpdateUserStatusRequest,
    session: Annotated[Session, Depends(get_db)],
) -> UpdateUserStatusResponse:
    user = get_user_by_id(session, user_id)
    if user is None:
        raise NotFoundException("ユーザーが見つかりません")

    if user.account_type == AccountType.admin:
        raise BusinessException("管理者ロールのユーザーはこのAPIから更新できません")

    updated_user = update_user_status_in_db(session, user, body.is_active)

    return UpdateUserStatusResponse(
        user_id=uuid.UUID(updated_user.id),
        is_active=updated_user.is_active,
    )
