from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DITAT_TOKEN: str
    SAMSARA_TOKEN: str
    DUMMY_TOKEN: str

    # Database settings
    DB_USER: str
    DB_PASSWORD: str
    DB_HOST: str
    DB_NAME: str
    
    # Auth settings
    AUTH_ROUTER_PREFIX: str = "/auth"
    TOKEN_ENDPOINT: str = "/login"
    TOKEN_ENDPOINT_PATH: str = f"{AUTH_ROUTER_PREFIX}{TOKEN_ENDPOINT}"

    # JWT settings
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Slack Bot settings
    SLACK_BOT_TOKEN: str
    SLACK_CHANNEL: str

    class Config:
        env_file = ".env"

settings = Settings()
