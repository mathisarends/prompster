from fastapi_canon.integrations.database import run_alembic_environment

# fastapi-canon db supplies the connection and the metadata of the Tables that
# the application's features contribute.
run_alembic_environment()
