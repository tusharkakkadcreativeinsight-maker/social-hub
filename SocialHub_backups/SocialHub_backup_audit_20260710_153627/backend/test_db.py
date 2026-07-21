r"""Simple database connection test for SocialHub.

Run from Windows PowerShell inside the backend folder:

    cd "D:\social media\SocialHub\backend"
    python test_db.py

If the connection is correct, it prints the SQLite or PostgreSQL version.
"""

from sqlalchemy import text

# Importing models registers all tables on Base.metadata for create_all().
from app.models import models  # noqa: F401
from app.database import Base, engine


def main():
    """Connect to the configured database, print version, then create missing tables."""

    dialect = engine.dialect.name
    database_name = "SQLite" if dialect == "sqlite" else "PostgreSQL" if dialect.startswith("postgresql") else dialect
    version_sql = "SELECT sqlite_version();" if dialect == "sqlite" else "SELECT version();"

    print(f"Connecting to {database_name}...")

    with engine.connect() as connection:
        version = connection.execute(text(version_sql)).scalar_one()
        print("Connection successful!")
        print(f"{database_name} version:")
        print(version)

    print("Creating tables if they do not already exist...")
    Base.metadata.create_all(bind=engine)
    print("Tables are ready.")


if __name__ == "__main__":
    main()