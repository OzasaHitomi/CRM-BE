from fastapi.requests import Request
from fastapi.responses import JSONResponse

from crm_be.core.config.base import core_settings
from crm_be.loggers.custom_logger import logger
from crm_be.schemas.v1.response.error import ErrorResponse


def handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error(
        f"予期しないエラーが発生しました: {request.method} {request.url.path}", exc_info=exc
    )

    content = ErrorResponse(detail="システムエラーが発生しました。")

    response = JSONResponse(
        status_code=500,
        content=content.model_dump(exclude_none=True),
    )

    response.headers["Access-Control-Allow-Origin"] = core_settings.frontend_base_url
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Allow-Methods"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "*"

    return response
