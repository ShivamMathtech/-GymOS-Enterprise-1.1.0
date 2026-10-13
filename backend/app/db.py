from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.database import build_engine

engine = build_engine(settings().database_url, pool_size=settings().database_pool_size)
SessionLocal = sessionmaker(engine, expire_on_commit=False)


def get_db():
    with SessionLocal() as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
