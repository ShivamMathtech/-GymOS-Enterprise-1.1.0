from logging.config import fileConfig
from alembic import context
from app.config import settings
from app.models import Base
from app.database import build_engine

config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)
url = settings().database_url
target_metadata = Base.metadata
if context.is_offline_mode():
    context.configure(
        url=url, target_metadata=target_metadata, literal_binds=True, dialect_opts={"paramstyle": "named"}
    )
    with context.begin_transaction():
        context.run_migrations()
else:
    engine = build_engine(url, migration=True)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()
