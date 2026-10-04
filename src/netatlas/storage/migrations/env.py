"""Only programmatic, explicit connections; no credentials in Alembic INI."""

from alembic import context

context.configure(connection=context.config.attributes["connection"])
with context.begin_transaction():
    context.run_migrations()
