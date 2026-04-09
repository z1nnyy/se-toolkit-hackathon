from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="Cava Menu API", alias="CAVA_NAME")
    debug: bool = Field(default=False, alias="CAVA_DEBUG")
    address: str = Field(default="127.0.0.1", alias="CAVA_ADDRESS")
    port: int = Field(default=8000, alias="CAVA_PORT")
    reload: bool = Field(default=False, alias="CAVA_RELOAD")

    cors_origins: list[str] = Field(
        default=["http://localhost:5173"],
        alias="CAVA_CORS_ORIGINS",
    )
    database_url: str = Field(
        default="sqlite+aiosqlite:///./data/cava-menu.db",
        alias="CAVA_DATABASE_URL",
    )
    menu_render_cache_dir: str = Field(
        default="./data/menu-render-cache",
        alias="CAVA_MENU_RENDER_CACHE_DIR",
    )
    seed_demo_data: bool = Field(default=True, alias="CAVA_SEED_DEMO_DATA")
    auth_session_hours: int = Field(default=12, alias="CAVA_AUTH_SESSION_HOURS")
    superadmin_username: str = Field(default="owner", alias="CAVA_SUPERADMIN_USERNAME")
    superadmin_password: str = Field(default="owner12345", alias="CAVA_SUPERADMIN_PASSWORD")
    superadmin_full_name: str = Field(
        default="Main Administrator",
        alias="CAVA_SUPERADMIN_FULL_NAME",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
