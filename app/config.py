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

    # JWT settings
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    class Config:
        env_file = ".env"

settings = Settings()
