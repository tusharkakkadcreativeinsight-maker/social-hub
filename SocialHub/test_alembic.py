import os
from alembic.config import Config

config = Config("backend/alembic.ini")
print("Before set:", config.get_main_option("sqlalchemy.url"))
print("Section before:", config.get_section(config.config_ini_section)["sqlalchemy.url"])

config.set_main_option("sqlalchemy.url", "postgresql://test:test@remote:5432/db")
print("After set:", config.get_main_option("sqlalchemy.url"))
print("Section after:", config.get_section(config.config_ini_section)["sqlalchemy.url"])
