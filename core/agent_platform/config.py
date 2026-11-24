from __future__ import annotations

from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AGENT_", env_file=".env", extra="ignore")

    llm_model: str = "groq:llama-3.3-70b-versatile"
    # Comma-separated "provider:model" list tried in order when the primary call fails (429, 5xx).
    fallback_models: str = ""
    llm_temperature: float = 0.2
    max_output_tokens: int = 1024

    internal_key: SecretStr = SecretStr("")
    demo_mode: bool = False

    mcp_servers_file: str = "config/mcp_servers.json"
    data_dir: str = "data"
    ui_dir: str = "ui/dist"

    max_model_calls: int = 8
    max_tool_calls: int = 6
    max_input_chars: int = 2000
    max_tool_result_chars: int = 4000
    daily_chat_cap: int = 50

    kill_switch: bool = False
    kill_switch_file: str = ""

    app_name: str = "Agent Platform"
    extra_prompt: str = ""
    disclaimer: str = (
        "This assistant explains data only. It is not financial, legal or medical advice."
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
