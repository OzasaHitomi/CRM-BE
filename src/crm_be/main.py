from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from crm_be.api.router import api_router
from crm_be.core.config.base import core_settings
from crm_be.exceptions.business_exception import BusinessException
from crm_be.handlers import (
    business_exception_handler,
    server_exception_handler,
    validation_exception_handler,
)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[core_settings.frontend_base_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")
app.add_exception_handler(RequestValidationError, validation_exception_handler.handler)  # type: ignore[arg-type]
app.add_exception_handler(BusinessException, business_exception_handler.handler)  # type: ignore[arg-type]
app.add_exception_handler(Exception, server_exception_handler.handler)
