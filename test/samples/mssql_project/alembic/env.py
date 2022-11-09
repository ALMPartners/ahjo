from __future__ import with_statement

import os
import sys
from logging import getLogger
from logging.config import fileConfig

from alembic import context
from sqlalchemy import MetaData, create_engine
from sqlalchemy.orm import declarative_base

from ahjo.database_utilities import create_conn_info, create_sqlalchemy_url, create_sqlalchemy_engine
from ahjo.interface_methods import load_json_conf

# Import from project root
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# This is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Line below is commented because of pytest's caplog fixture!
# This does not affect Ahjo's functionality, since this line exists solely
# so that Alembic can be used independently
# fileConfig(config.config_file_name, disable_existing_loggers=False)
logger = getLogger('alembic.env.py')

# Load project config file (config_development.jsonc)
main_config_path = context.get_x_argument(as_dictionary=True).get('main_config')
if main_config_path is None:
    logger.info('No extra alembic argument "-x main_config=config.file" given.')
    main_config_path = input("Module configuration file path: ")
logger.info(f'Main config file: {main_config_path}')

main_config = load_json_conf(main_config_path)
conn_info = create_conn_info(main_config)

version_table_schema = main_config.get("alembic_version_table_schema", "dbo")
version_table = main_config.get("alembic_version_table", "alembic_version")

###################################################################

meta = MetaData(naming_convention={
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s"
      })
Base = declarative_base(metadata=meta)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=create_sqlalchemy_url(conn_info), target_metadata=target_metadata, literal_binds=True)

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = create_sqlalchemy_engine(
        create_sqlalchemy_url(conn_info), 
        conn_info.get("token")
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
			version_table_schema=version_table_schema,
			version_table=version_table
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
