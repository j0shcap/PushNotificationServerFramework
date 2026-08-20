"""SQLAlchemy DB Engine for FastAPI dependency injection."""

import sqlalchemy
from sqlalchemy.orm import Session

from utils import getenv


def _engine_str(name: str = getenv("DB_NAME")) -> str:
    """
    Helper function for reading settings from environment variables to produce connection string.

    Arguments:
        name (str): The name of the database. Defaults to the value of the
            "DB_NAME" environment variable.

    Returns:
        str: The connection string for the database.
    """
    dialect = "postgresql+psycopg2"
    user = getenv("DB_USERNAME")
    password = getenv("DB_PASSWORD")
    host = getenv("DB_HOST")
    port = getenv("DB_PORT")
    return f"{dialect}://{user}:{password}@{host}:{port}/{name}"


engine = sqlalchemy.create_engine(_engine_str(), echo=True)
"""Application-level SQLAlchemy database engine."""


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
