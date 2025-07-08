from sqlmodel import create_engine
from config import settings
from urllib.parse import quote

DATABASE_URL = f"mysql+pymysql://{settings.DB_USER}:{quote(settings.DB_PASSWORD)}@{settings.DB_HOST}/{settings.DB_NAME}"

engine = create_engine(DATABASE_URL, echo=True)
