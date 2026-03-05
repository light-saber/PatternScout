from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
import sqlite3

# Create engine
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}
)

# Enable SQLite vector extension if available
@event.listens_for(engine, "connect")
def setup_sqlite(dbapi_conn, connection_record):
    if isinstance(dbapi_conn, sqlite3.Connection):
        if not hasattr(dbapi_conn, "enable_load_extension"):
            return

        try:
            dbapi_conn.enable_load_extension(True)
            dbapi_conn.load_extension("vec0")
        except Exception:
            pass  # sqlite-vec not installed, continue without vector support

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
