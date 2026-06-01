from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """從 .env 讀取設定。缺少的祕密在用到時才會報錯，不阻擋 app 啟動。"""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    openai_api_key: str = ""
    # 可選：自架 / Azure / 相容端點的 base url（留空用 OpenAI 官方）
    openai_base_url: str = ""
    wbs_model: str = "gpt-4o"

    jira_base_url: str = ""
    jira_email: str = ""
    jira_api_token: str = ""

    frontend_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    data_dir: str = "./data"

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.frontend_origins.split(",") if o.strip()]

    @property
    def jira_configured(self) -> bool:
        return bool(self.jira_base_url and self.jira_email and self.jira_api_token)

    @property
    def openai_configured(self) -> bool:
        return bool(self.openai_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
