from pathlib import Path

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    # 使用固定路径读取后端配置，避免启动目录改变时找错文件。
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
    )

    sqlite_path: Path = Path("data/customer_service.db")
    chroma_dir: Path = Path("data/chroma")
    bge_model_name: str = "BAAI/bge-small-zh-v1.5"
    bge_cache_dir: Path = Path("data/models")

    # 健康检查允许缺省密钥，配置对象的默认显示会隐藏密钥。
    deepseek_api_key: SecretStr | None = None
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-flash"
    auth_session_hours: int = Field(default=24, ge=1, le=720)

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        # 应用配置来自后端 .env，避免系统环境变量覆盖项目配置和密钥。
        return init_settings, dotenv_settings

    @field_validator("sqlite_path", "chroma_dir", "bge_cache_dir")
    @classmethod
    def resolve_backend_path(cls, path: Path) -> Path:
        # pathlib 会保留绝对路径，并将相对路径拼接到后端目录。
        return BACKEND_DIR / path
