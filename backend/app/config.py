from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Triage Desk"
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/triagedesk"
    SECRET_KEY: str = "change-this-in-production-use-a-long-random-string"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    ANTHROPIC_API_KEY: str = ""
    DEBUG: bool = False

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
