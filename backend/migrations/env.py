from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import os

# Import Base from your app
from app.database import Base

# Import your models so they are registered with Base.metadata
# (add this line even if you have no models yet; it will be used later)
from app import models  # noqa

# this is the Alembic Config object
config = context.config

# Override the sqlalchemy.url from environment variable
database_url = os.getenv("DATABASE_URL")
if database_url:
    config.set_main_option("sqlalchemy.url", database_url)

# Set target_metadata to your Base's metadata
target_metadata = Base.metadata

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()