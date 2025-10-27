from sqlmodel import create_engine
from sqlalchemy.engine.url import URL
from sqlalchemy import event

# from app.config import settings  # assuming this loads from .env


DATABASE_URL = URL.create(
    drivername="postgresql+psycopg2",
    username="postgres.pglonnvzqjpsqgqkvwtj",
    password="LceL1WNtneKOwdFa",
    host="aws-1-ap-northeast-1.pooler.supabase.com",
    port="5432",
    database="postgres",
)

vector_engine = create_engine(
    DATABASE_URL,
    echo=True,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600,
    connect_args={"connect_timeout": 10, "application_name": "fastapi-backend"},
)


@event.listens_for(vector_engine, "connect")
def set_search_path(dbapi_connection, connection_record):
    with dbapi_connection.cursor() as cursor:
        cursor.execute("SET search_path TO public")
