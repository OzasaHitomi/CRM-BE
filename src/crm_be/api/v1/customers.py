import uuid

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from crm_be.api.common.dependencies.authentication import get_current_user
from crm_be.api.common.dependencies.authorization import user_checker
from crm_be.api.common.dependencies.database import get_db
from crm_be.exceptions.forbidden_exception import ForbiddenException
from crm_be.exceptions.not_found_exception import NotFoundException
from crm_be.models.customer import Customer
from crm_be.models.deal import Deal
from crm_be.models.user import User
from crm_be.repositories.customer.repository import (
    assign_customer_user as assign_customer_user_in_db,
    create_customer as create_customer_in_db,
    get_customer_by_id,
    get_customers as get_customers_in_db,
    unassign_customer_user as unassign_customer_user_in_db,
    update_customer as update_customer_in_db,
)
from crm_be.repositories.deal.repository import create_deal as create_deal_in_db
from crm_be.schemas.v1.request.customer import CreateCustomerRequest, UpdateCustomerRequest
from crm_be.schemas.v1.request.deal import CreateDealRequest
from crm_be.schemas.v1.response.customer import (
    ActivityLogResponseItem,
    AssignCustomerUserResponse,
    AssignedUserResponseItem,
    CreateCustomerResponse,
    DealResponseItem,
    GetCustomerResponse,
    GetCustomersResponse,
    GetCustomersResponseItem,
    PaginationResponseItem,
    UpdateCustomerResponse,
)
from crm_be.store.enums.account_type import AccountType
from crm_be.store.enums.deal_status import DealStatus
from crm_be.store.enums.industry_type import IndustryType

router = APIRouter()


@router.get("", response_model=GetCustomersResponse)
def get_customers(
    session: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    # 業界で絞り込む。未指定時はNoneとなり、リポジトリ層で絞り込みなし(全業界)として扱われる。
    industry: IndustryType | None = None,
    # FEからのクエリパラメータ（例: /customers?page=2&pageSize=20）を受け取る。
    # ge=1: 1未満の値が来たら422エラーにする（0ページ目やマイナスページを弾く）
    page: Annotated[int, Query(ge=1)] = 1,
    # le=100: 過大なpage_sizeを指定されてパフォーマンスが悪化しないよう上限を設ける
    # alias: レスポンス（pageSize等）とキー名の表記を揃えるためキャメルケースにする
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 10,
) -> GetCustomersResponse:
    visible_to_user_id = current_user.id if current_user.account_type == AccountType.sales else None

    # 該当ページの顧客一覧と、絞り込み後の総件数の両方をリポジトリから受け取る
    customers, total_count = get_customers_in_db(
        session, visible_to_user_id, industry=industry, page=page, page_size=page_size
    )

    response_items = []
    for customer in customers:
        assigned_user = (
            AssignedUserResponseItem(
                user_id=uuid.UUID(customer.assigned_user.id),
                name=customer.assigned_user.name,
            )
            if customer.assigned_user is not None
            else None
        )
        response_items.append(
            GetCustomersResponseItem(
                customer_id=uuid.UUID(customer.id),
                company_name=customer.company_name,
                industry=customer.industry,
                assigned_user=assigned_user,
            )
        )

    # 総ページ数を計算する。
    # //は「割り算の結果を切り捨てて整数にする」演算子（例: 11 // 10 = 1）。
    # ただの total_count // page_size だと余りが切り捨てられてページが1つ足りなくなるため、
    # 先に (page_size - 1) を足すことで「1件でも余りがあれば1ページ繰り上げる」効果を出している。
    # 例）total_count=11, page_size=10 のとき (11+10-1)//10 = 20//10 = 2ページ
    total_pages = (total_count + page_size - 1) // page_size

    return GetCustomersResponse(
        customers=response_items,
        pagination=PaginationResponseItem(
            page=page,
            page_size=page_size,
            total_count=total_count,
            total_pages=total_pages,
        ),
    )


@router.get("/{customer_id}", response_model=GetCustomerResponse)
def get_customer(
    customer_id: uuid.UUID,
    session: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> GetCustomerResponse:
    customer = get_customer_by_id(session, str(customer_id))
    if customer is None:
        raise NotFoundException("customerが見つかりません")

    if (
        current_user.account_type == AccountType.sales
        and customer.assigned_user_id != current_user.id
    ):
        raise ForbiddenException("このcustomerを閲覧する権限がありません")

    assigned_user = (
        AssignedUserResponseItem(
            user_id=uuid.UUID(customer.assigned_user.id),
            name=customer.assigned_user.name,
        )
        if customer.assigned_user is not None
        else None
    )

    deals = [
        DealResponseItem(
            deal_id=uuid.UUID(deal.id),
            title=deal.title,
            status=deal.status,
            amount=deal.amount,
            plan=deal.plan,
            license_count=deal.license_count,
            contract_period=deal.contract_period,
            created_at=deal.created_at,
            activity_logs=[
                ActivityLogResponseItem(
                    activity_log_id=uuid.UUID(activity_log.id),
                    type=activity_log.type,
                    activity_date=activity_log.activity_date,
                    note=activity_log.note,
                )
                for activity_log in deal.activity_logs
            ],
        )
        for deal in customer.deals
    ]

    return GetCustomerResponse(
        customer_id=uuid.UUID(customer.id),
        company_name=customer.company_name,
        industry=customer.industry,
        company_size=customer.company_size,
        contact_name=customer.contact_name,
        phone=customer.phone,
        email=customer.email,
        assigned_user=assigned_user,
        deals=deals,
    )


@router.post(
    "",
    status_code=201,
    response_model=CreateCustomerResponse,
    dependencies=[Depends(user_checker({AccountType.sales, AccountType.manager}))],
)
def create_customer(
    body: CreateCustomerRequest,
    session: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> CreateCustomerResponse:
    is_sales = current_user.account_type == AccountType.sales

    customer = Customer(
        company_name=body.company_name,
        industry=body.industry,
        company_size=body.company_size,
        contact_name=body.contact_name,
        phone=body.phone,
        email=body.email,
        assigned_user_id=current_user.id if is_sales else None,
    )
    created_customer = create_customer_in_db(session, customer)

    assigned_user = (
        AssignedUserResponseItem(
            user_id=uuid.UUID(created_customer.assigned_user.id),
            name=created_customer.assigned_user.name,
        )
        if created_customer.assigned_user is not None
        else None
    )

    return CreateCustomerResponse(
        customer_id=uuid.UUID(created_customer.id),
        company_name=created_customer.company_name,
        industry=created_customer.industry,
        company_size=created_customer.company_size,
        contact_name=created_customer.contact_name,
        phone=created_customer.phone,
        email=created_customer.email,
        assigned_user=assigned_user,
    )


@router.put(
    "/{customer_id}",
    response_model=UpdateCustomerResponse,
    dependencies=[Depends(user_checker({AccountType.sales, AccountType.manager}))],
)
def update_customer(
    customer_id: uuid.UUID,
    body: UpdateCustomerRequest,
    session: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> UpdateCustomerResponse:
    customer = get_customer_by_id(session, str(customer_id), for_update=True)
    if customer is None:
        raise NotFoundException("customerが見つかりません")

    if (
        current_user.account_type == AccountType.sales
        and customer.assigned_user_id != current_user.id
    ):
        raise ForbiddenException("このcustomerを編集する権限がありません")

    updated_customer = update_customer_in_db(
        session,
        customer,
        company_name=body.company_name,
        industry=body.industry,
        company_size=body.company_size,
        contact_name=body.contact_name,
        phone=body.phone,
        email=body.email,
    )

    assigned_user = (
        AssignedUserResponseItem(
            user_id=uuid.UUID(updated_customer.assigned_user.id),
            name=updated_customer.assigned_user.name,
        )
        if updated_customer.assigned_user is not None
        else None
    )

    return UpdateCustomerResponse(
        customer_id=uuid.UUID(updated_customer.id),
        company_name=updated_customer.company_name,
        industry=updated_customer.industry,
        company_size=updated_customer.company_size,
        contact_name=updated_customer.contact_name,
        phone=updated_customer.phone,
        email=updated_customer.email,
        assigned_user=assigned_user,
    )


@router.post(
    "/{customer_id}/deals",
    status_code=201,
    response_model=DealResponseItem,
    dependencies=[Depends(user_checker({AccountType.sales, AccountType.manager}))],
)
def create_deal(
    customer_id: uuid.UUID,
    body: CreateDealRequest,
    session: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> DealResponseItem:
    customer = get_customer_by_id(session, str(customer_id), for_update=True)
    if customer is None:
        raise NotFoundException("customerが見つかりません")

    if (
        current_user.account_type == AccountType.sales
        and customer.assigned_user_id != current_user.id
    ):
        raise ForbiddenException("このcustomerにdealを作成する権限がありません")

    deal = Deal(
        customer_id=customer.id,
        title=body.title,
        status=DealStatus.lead,
        amount=body.amount,
        plan=body.plan,
        license_count=body.license_count,
        contract_period=body.contract_period,
    )
    created_deal = create_deal_in_db(session, deal)

    return DealResponseItem(
        deal_id=uuid.UUID(created_deal.id),
        title=created_deal.title,
        status=created_deal.status,
        amount=created_deal.amount,
        plan=created_deal.plan,
        license_count=created_deal.license_count,
        contract_period=created_deal.contract_period,
        created_at=created_deal.created_at,
        activity_logs=[],
    )


@router.put(
    "/{customer_id}/assigned-user",
    response_model=AssignCustomerUserResponse,
    dependencies=[Depends(user_checker({AccountType.sales, AccountType.manager}))],
)
def assign_customer_user(
    customer_id: uuid.UUID,
    session: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> AssignCustomerUserResponse:
    customer = get_customer_by_id(session, str(customer_id), for_update=True)
    if customer is None:
        raise NotFoundException("customerが見つかりません")

    if customer.assigned_user_id is not None and customer.assigned_user_id != current_user.id:
        raise ForbiddenException("既に他の担当者にアサインされています")

    updated_customer = assign_customer_user_in_db(session, customer, current_user.id)

    return AssignCustomerUserResponse(
        customer_id=uuid.UUID(updated_customer.id),
        assigned_user=AssignedUserResponseItem(
            user_id=uuid.UUID(current_user.id),
            name=current_user.name,
        ),
    )


@router.delete("/{customer_id}/assigned-user", status_code=204)
def unassign_customer_user(
    customer_id: uuid.UUID,
    session: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    customer = get_customer_by_id(session, str(customer_id), for_update=True)
    if customer is None:
        raise NotFoundException("customerが見つかりません")

    if (
        current_user.account_type == AccountType.sales
        and customer.assigned_user_id is not None
        and customer.assigned_user_id != current_user.id
    ):
        raise ForbiddenException("他の担当者にアサインされているため解除する権限がありません")

    unassign_customer_user_in_db(session, customer)
