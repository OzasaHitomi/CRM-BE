from typing import Literal

from pydantic_settings import BaseSettings


# BaseSettings は環境変数を参照して同一名をセットする(load dotenv 等は不要)
class CoreSettings(BaseSettings):
    # デプロイ先の種別。production では起動時のシード処理を実行しない（誤って本番にadmin等を投入するのを防ぐ）
    environment: Literal["local", "production"] = "local"
    seed_profile: Literal["none", "development", "e2e"]
    cookie_secure: bool
    frontend_base_url: str = "http://localhost:5173"
    db_connection: str = "mysql"
    mysql_host: str = "localhost"
    mysql_port: int = 3306
    mysql_database: str = "crm"
    mysql_user: str = "user"
    mysql_password: str = "pass"
    secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24

    @property
    def database_url(self) -> str:
        return (
            f"{self.db_connection}://"
            f"{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"
        )

    model_config = {"env_file": ".env", "extra": "ignore"}


core_settings = CoreSettings()  # type: ignore[call-arg]
