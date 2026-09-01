from fastapi.requests import Request
from fastapi.responses import JSONResponse

from crm_be.exceptions.business_exception import BusinessException
from crm_be.schemas.v1.response.error import ErrorResponse


def handler(request: Request, exc: BusinessException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(type=exc.type, detail=str(exc.detail)).model_dump(exclude_none=True),
    )
