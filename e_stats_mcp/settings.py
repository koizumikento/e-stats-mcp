"""環境変数設定."""

import os
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """環境変数設定."""

    # 環境変数から必須取得。未設定なら初期化時に KeyError を発生させる。
    E_STAT_APP_ID: str = Field(default_factory=lambda: os.environ["E_STAT_APP_ID"])

    model_config = SettingsConfigDict(env_prefix="", env_file=None, extra="ignore")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """設定を取得（キャッシュ済み）."""
    return Settings()

