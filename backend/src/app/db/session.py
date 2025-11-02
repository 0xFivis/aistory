import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.env import load_env

load_env()

# Default to development database if not specified
DATABASE_URL = os.getenv('DATABASE_URL', 'mysql+pymysql://root:root@localhost/aistory?charset=utf8mb4')

# Create engine without any SQLite-specific arguments
engine = create_engine(
    DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800  # Recycle connections after 30 minutes
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
