from fastapi import APIRouter

from crm_be.api.v1.admin.router import router as admin_router
from crm_be.api.v1.auth import router as auth_router
from crm_be.api.v1.customers import router as customers_router
from crm_be.api.v1.deals import router as deals_router
from crm_be.api.v1.healthcheck import router as healthcheck_router

router = APIRouter()
router.include_router(admin_router, prefix="/admin")
router.include_router(auth_router, prefix="/auth", tags=["Auth"])
router.include_router(customers_router, prefix="/customers", tags=["Customers"])
router.include_router(deals_router, prefix="/deals", tags=["Deals"])
router.include_router(healthcheck_router, prefix="/healthcheck", tags=["Healthcheck"])
