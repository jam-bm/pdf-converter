from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.core.config import settings

sync_engine = create_engine(settings.DATABASE_SYNC_URL, echo=False, pool_pre_ping=True)
SyncSessionLocal = sessionmaker(bind=sync_engine)


def get_sync_db() -> Session:
    return SyncSessionLocal()
