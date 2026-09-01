from fastapi import status
from fastapi.exceptions import RequestValidationError
from fastapi.requests import Request
from fastapi.responses import JSONResponse

from crm_be.schemas.v1.response.error import ErrorResponse, ValidationErrorResponseItem


def handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    detail: list[ValidationErrorResponseItem] = []
    for error in exc.errors():
        item = ValidationErrorResponseItem(
            loc=error["loc"],
            type=error["type"],
            msg=error["msg"],
        )
        detail.append(item)

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content=ErrorResponse(type="VALIDATION_ERROR", detail=detail).model_dump(exclude_none=True),
    )
