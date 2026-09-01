from fastapi import APIRouter

from .users import router as user_router

COMMON_TAGS_NAME = "Admin"

router = APIRouter()
router.include_router(user_router, prefix="/users", tags=[f"{COMMON_TAGS_NAME} - Users"])
