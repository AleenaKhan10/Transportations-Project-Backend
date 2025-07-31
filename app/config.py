from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DITAT_TOKEN: str
    SAMSARA_TOKEN: str
    DUMMY_TOKEN: str
    WEBHOOK_TOKEN: str

    # Database settings
    DB_USER: str
    DB_PASS: str
    DB_HOST: str | None = None
    DB_NAME: str
    
    # Cloud Run specific settings for Database. 
    # For eg: `/cloudsql/agy-intelligence-hub:us-central1:agy-intelligence-hub-instance`
    INSTANCE_UNIX_SOCKET: str | None = None
    
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
    ALERTS_APPROACH1_SLACK_CHANNEL: str = "#ai-temp-testing"
    ALERTS_APPROACH2_SLACK_CHANNEL: str = "#ai-temp-alerts"


    # VAPI settings
    VAPI_API_KEY: str = ""
    VAPI_ASSISTANT_ID: str = ""

    # Application settings
    PORT: int = 8000

    # PCMiler settings
    PCMILER_API_KEY: str = ""

    # VAPI Phone Number ID (required for campaigns)
    VAPI_PHONENUMBER_ID: str = ""

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
