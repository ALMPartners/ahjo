from os import listdir, path
from re import DOTALL, sub

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine.url import URL
from sqlalchemy.sql import text

VIEWS_DIR = './database/views'
PROC_DIR = './database/procedures'
FUNC_DIR = './database/functions'
MSSQL_COMMENTS = [r'/\*.+?\*/', r'--.[ \S]+?\n']
MSSQL_BATCH_SEP = '\nGO'


@pytest.fixture(scope='session')
def mssql_sample(prepared_sample):
    return prepared_sample(
        sample_name='mssql_project',
        host_param='mssql_host',
        port_param='mssql_port',
        usrn_param='mssql_username',
        pass_param='mssql_password'
    )


@pytest.fixture(scope='session')
def mssql_master_engine(request, ahjo_config, mssql_sample):
    """Create engine for MSSQL server master database.
    """
    config = ahjo_config(mssql_sample)
    connection_url = URL(
        drivername="mssql+pyodbc",
        username=request.config.getoption('mssql_username'),
        password=request.config.getoption('mssql_password'),
        host=config['target_server_hostname'],
        port=config['sql_port'],
        database='master',
        query={'driver': config['sql_driver']}
    )
    return create_engine(connection_url)


@pytest.fixture(scope='session')
def mssql_engine(request, ahjo_config, mssql_sample):
    """Create engine for MSSQL server test database.
    """
    config = ahjo_config(mssql_sample)
    connection_url = URL(
        drivername="mssql+pyodbc",
        username=request.config.getoption('mssql_username'),
        password=request.config.getoption('mssql_password'),
        host=config['target_server_hostname'],
        port=config['sql_port'],
        database=config['target_database_name'],
        query={'driver': config['sql_driver']}
    )
    return create_engine(connection_url)


@pytest.fixture(scope='session')
def mssql_setup_and_teardown(mssql_master_engine, test_db_name):
    """
    What this fixture does:
        - Init database for testing.
        - Execute mssql tests.
        - Delete database.
    """
    with mssql_master_engine.connect() as connection:
        connection.execution_options(isolation_level="AUTOCOMMIT")
        connection.execute(f'CREATE DATABASE {test_db_name}')
    yield
    with mssql_master_engine.connect() as connection:
        connection.execution_options(isolation_level="AUTOCOMMIT")
        result = connection.execute(
            'SELECT session_id FROM sys.dm_exec_sessions WHERE database_id = DB_ID(?)', (test_db_name,))
        for row in result.fetchall():
            connection.execute(f'KILL {row.session_id}')
        connection.execute(f'DROP DATABASE {test_db_name}')


@pytest.fixture(scope='function')
def deploy_mssql_objects():
    """When executing, CWD must be set correctly to sample root!"""
    def deploy_objects(engine):
        w_files = [path.join(VIEWS_DIR, f) for f in listdir(VIEWS_DIR)]
        p_files = [path.join(PROC_DIR, f) for f in listdir(PROC_DIR)]
        f_files = [path.join(FUNC_DIR, f) for f in listdir(FUNC_DIR)]
        files = w_files + p_files + f_files
    
        for tsql in files:
            with open(tsql, 'r', encoding='utf-8-sig') as f:
                t_sql = f.read()
            for comment in MSSQL_COMMENTS:
                t_sql = sub(comment, '', t_sql, flags=DOTALL)
            batches = t_sql.split(MSSQL_BATCH_SEP)
    
            with engine.connect() as connection:
                connection.execution_options(isolation_level='AUTOCOMMIT')
                for batch in batches:
                    if not batch:
                        continue
                    batch = sub(':', r'\:', batch)
                    connection.execute(text(batch))
    return deploy_objects


@pytest.fixture(scope='function')
def drop_mssql_objects():
    """When executing, CWD must be set correctly to sample root!"""
    def drop_objects(engine):
        w_objects = [f"VIEW [{f.split('.')[0]}].[{f.split('.')[1]}]" for f in listdir(VIEWS_DIR)]
        p_objects = [f"PROCEDURE [{f.split('.')[0]}].[{f.split('.')[1]}]" for f in listdir(PROC_DIR)]
        f_objects = [f"FUNCTION [{f.split('.')[0]}].[{f.split('.')[1]}]" for f in listdir(FUNC_DIR)]
        database_objects = w_objects + p_objects + f_objects
    
        for db_object in database_objects:
            with engine.connect() as connection:
                connection.execution_options(isolation_level='AUTOCOMMIT')
                connection.execute(text(f"BEGIN TRY DROP {db_object} END TRY BEGIN CATCH END CATCH"))
    return drop_objects
