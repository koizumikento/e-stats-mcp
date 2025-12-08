"""環境変数設定."""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """環境変数設定."""

    E_STAT_API_KEY: str

    model_config = SettingsConfigDict(env_prefix="", env_file=None, extra="ignore")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """設定を取得（キャッシュ済み）."""
    return Settings()

