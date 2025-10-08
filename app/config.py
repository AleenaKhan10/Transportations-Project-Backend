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
    DB_PORT: int
    
    # Cloud Run specific settings for Database. 
    # For eg: `/cloudsql/agy-intelligence-hub:us-central1:agy-intelligence-hub-instance`
    INSTANCE_UNIX_SOCKET: str | None = None
    
    # Cloud Run URL
    CLOUD_RUN_URL: str = "https://agy-backend-181509438418.us-central1.run.app"

    # Auth settings
    AUTH_ROUTER_PREFIX: str = "/auth"
    TOKEN_ENDPOINT: str = "/login"
    TOKEN_ENDPOINT_PATH: str = f"{AUTH_ROUTER_PREFIX}{TOKEN_ENDPOINT}"

    # JWT settings
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 24 * 60 # 24 hours

    # Slack Bot settings
    SLACK_BOT_TOKEN: str
    SLACK_SIGNING_SECRET: str
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
    
    # Weather API settings
    WEATHER_API_KEY: str = ""
    WEATHER_API_BASE_URL: str = "http://api.weatherapi.com/v1"
    
    # Email settings
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SENDER_EMAIL: str = "aleenakhanraees40@gmail.com"
    SENDER_PASSWORD: str = ""

    # Sentry/GlitchTip settings
    SENTRY_DSN: str = ""
    SENTRY_ENVIRONMENT: str = "production"
    SENTRY_TRACES_SAMPLE_RATE: float = 1.0

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
