from fastapi import HTTPException, status


class BusinessException(HTTPException):
    def __init__(
        self, message: str = "業務エラーが発生しました", type: str = "BUSINESS_RULE_ERROR"
    ) -> None:
        super().__init__(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=message)
        self.type = type
