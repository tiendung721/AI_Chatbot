from alembic import context
from sqlalchemy import create_engine

from citizen_ai.config import settings

url = settings().migration_database_url.get_secret_value()
if not url:
    raise RuntimeError("MIGRATION_DATABASE_URL is required for migrations")
engine = create_engine(url, hide_parameters=True)
with engine.connect() as connection:
    context.configure(connection=connection, target_metadata=None)
    with context.begin_transaction():
        context.run_migrations()
