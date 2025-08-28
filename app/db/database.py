from sqlmodel import create_engine
from sqlalchemy.engine.url import URL
from sqlalchemy import event
from config import settings


DATABASE_URL = URL.create(
    drivername="postgresql+psycopg2",
    username=settings.DB_USER,
    password=settings.DB_PASS,
    host=settings.DB_HOST,
    port=settings.DB_PORT,
    database=settings.DB_NAME,
)

# For debugging purposes, print the database URL
print(f"Database URL: {DATABASE_URL}")

# Create engine with connection pooling and retry settings
engine = create_engine(
    DATABASE_URL, 
    echo=True,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,  # Validates connections before use
    pool_recycle=3600,   # Recycle connections after 1 hour
    connect_args={
        "connect_timeout": 10,
        "application_name": "agy-backend"
    }
)

# Set search path to dev schema after connection
@event.listens_for(engine, "connect")
def set_search_path(dbapi_connection, connection_record):
    with dbapi_connection.cursor() as cursor:
        cursor.execute("SET search_path TO dev, public")

# Also set search path on connection checkout to ensure it persists across pool recycling
@event.listens_for(engine, "checkout")
def set_search_path_on_checkout(dbapi_connection, connection_record, connection_proxy):
    with dbapi_connection.cursor() as cursor:
        cursor.execute("SET search_path TO dev, public")
