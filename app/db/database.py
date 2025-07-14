from sqlmodel import create_engine
from sqlalchemy.engine.url import URL
from sqlalchemy.util import EMPTY_DICT
from config import settings


DATABASE_URL = URL.create(
    drivername="mysql+pymysql",
    username=settings.DB_USER,
    password=settings.DB_PASS,
    host=settings.DB_HOST,
    database=settings.DB_NAME,
    query={"unix_socket": settings.INSTANCE_UNIX_SOCKET} if settings.INSTANCE_UNIX_SOCKET else EMPTY_DICT,
)

# For debugging purposes, print the database URL
print(f"Database URL: {DATABASE_URL}")

engine = create_engine(DATABASE_URL, echo=True)
