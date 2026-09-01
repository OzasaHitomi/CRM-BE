from fastapi import HTTPException, status


class ForbiddenException(HTTPException):
    def __init__(self, message: str = "認可エラー") -> None:
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=message)
