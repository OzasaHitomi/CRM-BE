from fastapi import APIRouter

router = APIRouter()


@router.get("")
def get_healthcheck() -> dict:
    return {"status": "ok"}
