import uuid

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from crm_be.api.common.dependencies.authentication import get_current_user
from crm_be.api.common.dependencies.authorization import user_checker
from crm_be.api.common.dependencies.database import get_db
from crm_be.exceptions.business_exception import BusinessException
from crm_be.exceptions.forbidden_exception import ForbiddenException
from crm_be.exceptions.not_found_exception import NotFoundException
from crm_be.logic.business.deal.status_transition import can_transition_deal_status
from crm_be.models.activity_log import ActivityLog
from crm_be.models.user import User
from crm_be.repositories.activity_log.repository import (
    create_activity_log as create_activity_log_in_db,
    get_activity_log_by_id,
    update_activity_log as update_activity_log_in_db,
)
from crm_be.repositories.deal.repository import (
    get_deal_by_id,
    update_deal as update_deal_in_db,
    update_deal_status as update_deal_status_in_db,
)
from crm_be.schemas.v1.request.activity_log import (
    CreateActivityLogRequest,
    UpdateActivityLogRequest,
)
from crm_be.schemas.v1.request.deal import UpdateDealRequest, UpdateDealStatusRequest
from crm_be.schemas.v1.response.activity_log import (
    CreateActivityLogResponse,
    UpdateActivityLogResponse,
)
from crm_be.schemas.v1.response.deal import UpdateDealResponse, UpdateDealStatusResponse
from crm_be.store.enums.account_type import AccountType

router = APIRouter()


@router.put(
    "/{deal_id}",
    response_model=UpdateDealResponse,
    dependencies=[Depends(user_checker({AccountType.sales, AccountType.manager}))],
)
def update_deal(
    deal_id: uuid.UUID,
    body: UpdateDealRequest,
    session: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> UpdateDealResponse:
    deal = get_deal_by_id(session, str(deal_id), for_update=True)
    if deal is None:
        raise NotFoundException("dealが見つかりません")

    if (
        current_user.account_type == AccountType.sales
        and deal.customer.assigned_user_id != current_user.id
    ):
        raise ForbiddenException("このdealを編集する権限がありません")

    updated_deal = update_deal_in_db(
        session,
        deal,
        title=body.title,
        amount=body.amount,
        plan=body.plan,
        license_count=body.license_count,
        contract_period=body.contract_period,
    )

    return UpdateDealResponse(
        deal_id=uuid.UUID(updated_deal.id),
        title=updated_deal.title,
        amount=updated_deal.amount,
        plan=updated_deal.plan,
        license_count=updated_deal.license_count,
        contract_period=updated_deal.contract_period,
    )


@router.put(
    "/{deal_id}/status",
    response_model=UpdateDealStatusResponse,
    dependencies=[Depends(user_checker({AccountType.sales, AccountType.manager}))],
)
def update_deal_status(
    deal_id: uuid.UUID,
    body: UpdateDealStatusRequest,
    session: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> UpdateDealStatusResponse:
    deal = get_deal_by_id(session, str(deal_id), for_update=True)
    if deal is None:
        raise NotFoundException("dealが見つかりません")

    if (
        current_user.account_type == AccountType.sales
        and deal.customer.assigned_user_id != current_user.id
    ):
        raise ForbiddenException("このdealを編集する権限がありません")

    if not can_transition_deal_status(deal.status):
        raise BusinessException("成約・失注済みのdealのステータスは変更できません")

    updated_deal = update_deal_status_in_db(session, deal, body.status)

    return UpdateDealStatusResponse(
        deal_id=uuid.UUID(updated_deal.id),
        status=updated_deal.status,
    )


@router.post(
    "/{deal_id}/activity-logs",
    status_code=201,
    response_model=CreateActivityLogResponse,
    dependencies=[Depends(user_checker({AccountType.sales, AccountType.manager}))],
)
def create_activity_log(
    deal_id: uuid.UUID,
    body: CreateActivityLogRequest,
    session: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> CreateActivityLogResponse:
    deal = get_deal_by_id(session, str(deal_id), for_update=True)
    if deal is None:
        raise NotFoundException("dealが見つかりません")

    if (
        current_user.account_type == AccountType.sales
        and deal.customer.assigned_user_id != current_user.id
    ):
        raise ForbiddenException("このdealに活動ログを作成する権限がありません")

    activity_log = ActivityLog(
        deal_id=deal.id,
        type=body.type,
        activity_date=body.activity_date,
        note=body.note,
    )
    created_activity_log = create_activity_log_in_db(session, activity_log)

    return CreateActivityLogResponse(
        activity_log_id=uuid.UUID(created_activity_log.id),
        type=created_activity_log.type,
        activity_date=created_activity_log.activity_date,
        note=created_activity_log.note,
    )


@router.put(
    "/{deal_id}/activity-logs/{activity_log_id}",
    response_model=UpdateActivityLogResponse,
    dependencies=[Depends(user_checker({AccountType.sales, AccountType.manager}))],
)
def update_activity_log(
    deal_id: uuid.UUID,
    activity_log_id: uuid.UUID,
    body: UpdateActivityLogRequest,
    session: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> UpdateActivityLogResponse:
    activity_log = get_activity_log_by_id(session, str(activity_log_id))
    if activity_log is None or activity_log.deal_id != str(deal_id):
        raise NotFoundException("活動ログが見つかりません")

    if (
        current_user.account_type == AccountType.sales
        and activity_log.deal.customer.assigned_user_id != current_user.id
    ):
        raise ForbiddenException("この活動ログを編集する権限がありません")

    updated_activity_log = update_activity_log_in_db(
        session,
        activity_log,
        type=body.type,
        activity_date=body.activity_date,
        note=body.note,
    )

    return UpdateActivityLogResponse(
        activity_log_id=uuid.UUID(updated_activity_log.id),
        type=updated_activity_log.type,
        activity_date=updated_activity_log.activity_date,
        note=updated_activity_log.note,
    )
