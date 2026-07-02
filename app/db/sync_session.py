from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from app.core.config import settings

sync_engine = create_engine(settings.DATABASE_SYNC_URL, echo=False, pool_pre_ping=True)

# For the local SQLite dev setup, enable WAL so the eager Celery task can write while
# the async API request still holds a read transaction, and wait on brief locks.
if sync_engine.dialect.name == "sqlite":
    @event.listens_for(sync_engine, "connect")
    def _sqlite_pragmas(dbapi_conn, _record):  # noqa: ANN001
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA busy_timeout=30000")
        cur.close()

SyncSessionLocal = sessionmaker(bind=sync_engine)


def get_sync_db() -> Session:
    return SyncSessionLocal()
