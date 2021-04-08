from argparse import Namespace
from os import listdir, path

from alembic import command
from alembic.config import Config
from sqlalchemy.sql import text

VIEWS_DIR = './database/views'
PROC_DIR = './database/procedures'
FUNC_DIR = './database/functions'


def run_alembic_action(action, target):
    """CWD must be set correctly to sample root!"""
    alembic_config = Config('alembic.ini')
    # main section options are set when main section is read
    main_section = alembic_config.config_ini_section
    alembic_config.get_section(main_section)
    alembic_config.cmd_opts = Namespace(
        x=["main_config=config_development.jsonc"])
    if action == 'upgrade':
        command.upgrade(alembic_config, target)
    elif action == 'downgrade':
        command.downgrade(alembic_config, target)


def deploy_database_objects(engine):
    """CWD must be set correctly to sample root!"""
    w_files = [path.join(VIEWS_DIR, f) for f in listdir(VIEWS_DIR)]
    p_files = [path.join(PROC_DIR, f) for f in listdir(PROC_DIR)]
    f_files = [path.join(FUNC_DIR, f) for f in listdir(FUNC_DIR)]
    files = w_files + p_files + f_files

    for tsql in files:
        print(tsql)
        with open(tsql, 'r') as f:
            t_sql = f.read()
        batches = t_sql.split('GO')

        with engine.connect() as connection:
            connection.execution_options(isolation_level='AUTOCOMMIT')
            for batch in batches:
                if not batch:
                    continue
                connection.execute(text(batch))


def drop_database_objects(engine):
    """CWD must be set correctly to sample root!"""
    w_objects = [f"VIEW {f}" for f in listdir(VIEWS_DIR)]
    p_objects = [f"PROCEDURE {f}" for f in listdir(PROC_DIR)]
    f_objects = [f"FUNCTION {f}" for f in listdir(FUNC_DIR)]
    database_objects = w_objects + p_objects + f_objects

    for db_object in database_objects:
        with engine.connect() as connection:
            connection.execution_options(isolation_level='AUTOCOMMIT')
            connection.execute(text(f"DROP {db_object}"))
