"""SQLAlchemy DB Engine for FastAPI dependency injection."""

import sqlalchemy
from sqlalchemy.orm import Session

from utils import getenv, getenv_bool


def _engine_str() -> str:
    """
    Helper function for reading settings from environment variables to produce connection string.

    Returns:
        str: The connection string for the database.
    """
    dialect = "postgresql+psycopg2"
    user = getenv("DB_USERNAME")
    password = getenv("DB_PASSWORD")
    host = getenv("DB_HOST")
    port = getenv("DB_PORT")
    name = getenv("DB_NAME")
    return f"{dialect}://{user}:{password}@{host}:{port}/{name}"


# Application-level SQLAlchemy database engine. SQL statement logging would
# include device tokens, so it is opt-in via DB_ECHO for local debugging only.
engine = sqlalchemy.create_engine(_engine_str(), echo=getenv_bool("DB_ECHO"))


def db_session():
    """
    Generator function offering dependency injection of SQLAlchemy Sessions.

    Yields:
        session: SQLAlchemy Session object
    """
    session = Session(engine)
    try:
        yield session
    finally:
        session.close()
