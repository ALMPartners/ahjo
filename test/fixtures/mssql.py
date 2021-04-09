import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine.url import URL


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
