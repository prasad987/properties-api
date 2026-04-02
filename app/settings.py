from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # MongoDB
    # Provide a default so imports/lint don't fail; override in `.env`.
    mongodb_url: str = "mongodb://localhost:27017"
    mongodb_db: str = "properties"
    mongodb_admin_collection: str = "admin_users"

    # JWT
    # Provide a default so imports/lint don't fail; override in `.env`.
    jwt_secret_key: str = "change-me-to-a-long-random-secret"
    jwt_algorithm: str = "HS256"
    jwt_access_token_exp_minutes: int = 60

    # CORS (optional)
    cors_allow_origins: list[str] = []

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()

