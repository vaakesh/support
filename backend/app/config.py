from functools import lru_cache
from pathlib import Path
from typing import Self

from pydantic import BaseModel, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent.parent
print(BASE_DIR)
class AuthJWT(BaseModel):
    base_dir: Path = BASE_DIR
    private_key_path: Path
    public_key_path: Path
    algorithm: str = "RS256"
    access_token_expire_minutes: int = 5
    refresh_token_expire_days: int = 7

    @model_validator(mode="after")
    def resolve_paths(self) -> Self:
        if not self.private_key_path.is_absolute():
            self.private_key_path = self.base_dir / self.private_key_path

        if not self.public_key_path.is_absolute():
            self.public_key_path = self.base_dir / self.public_key_path

        return self

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
    )
    db_host: str
    db_port: int
    db_name: str
    db_user: str
    db_password: str
    refresh_pepper: str

    def database_url(self) -> str:
        return f"postgresql+asyncpg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    auth_jwt: AuthJWT


@lru_cache()
def get_settings() -> Settings:
    return Settings()