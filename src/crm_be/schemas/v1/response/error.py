from crm_be.schemas.v1.response.base import BaseV1ResponseSchema


class ValidationErrorResponseItem(BaseV1ResponseSchema):
    loc: list[str | int]
    type: str
    msg: str


class ErrorResponse(BaseV1ResponseSchema):
    type: str | None = None
    detail: str | list[ValidationErrorResponseItem]
