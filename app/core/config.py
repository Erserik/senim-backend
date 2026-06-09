from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite+aiosqlite:///./senim.db"
    SECRET_KEY: str = "dev-secret-key-not-for-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 30  # 30 days (dev convenience)

    CORS_ORIGINS: str = (
        "http://localhost:5173,http://localhost:3000,http://localhost:4173,"
        "http://127.0.0.1:5173,http://127.0.0.1:3000,"
        "capacitor://localhost,http://localhost,ionic://localhost"
    )

    model_config = {"env_file": ".env", "extra": "ignore"}

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


settings = Settings()
