from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StringConstraints
from pydantic.alias_generators import to_camel
from pydantic.networks import EmailStr
from pydantic_core import PydanticCustomError


class BaseV1RequestSchema(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )


TrimmedStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
TrimmedStr20 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=20)]
TrimmedStr100 = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)
]
BoundedEmailStr = Annotated[EmailStr, StringConstraints(strip_whitespace=True, max_length=255)]
PositiveDatabaseInt = Annotated[int, Field(gt=0, le=2_147_483_647)]


def validate_password_byte_length(value: str) -> str:
    if len(value.encode("utf-8")) > 72:
        raise PydanticCustomError(
            "password_byte_length", "パスワードはUTF-8で72バイト以下にしてください"
        )
    return value


PasswordStr = Annotated[
    str,
    StringConstraints(min_length=8),
    AfterValidator(validate_password_byte_length),
]
