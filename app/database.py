"""
Database setup: SQLAlchemy engine, session factory, and declarative base.

"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base

from config import settings

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True, # checks connections are alive before using them
    future=True,
)

# session factory: each request gets its own Session 
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    future=True,
)

# Declarative base: all SQLAlchemy models (models.py) inherit from this
Base = declarative_base()

def init_db() -> None:
    """
    Called once on app start up (see main.py's startup)
    1. Ensures the pgvector extension is enabled in Postgres.
    2. Create all tables defined in models.py if they dont exist yet.

    """
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))

    # Import models here (not at top of file) to avoid circular imports, 
    # since models.py imports Base from this file
    import models # noqa: F401
    Base.metadata.create_all(bind=engine) 

def get_db():
    """
    FastAPI dependency that yields a database session and guarantees
    its closed after the request finishes, even if an error occurs.
    """

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()   
