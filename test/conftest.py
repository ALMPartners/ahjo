"""Pytest configuration.

Notice that MSSQL user must have permissions to master db
tox -- --mssql_host localhost --mssql_port 14330 --mssql_username sa --mssql_password SALA_kala12
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine.url import URL


def pytest_addoption(parser):
    parser.addoption(
        '--mssql_host',
        action='store',
        dest='mssql_host',
        help='SQL Server hostname used for tests.'
        )
    parser.addoption(
        '--mssql_port',
        action='store',
        default=1433,
        dest='mssql_port',
        help='SQL Server port number used for tests.'
        )
    parser.addoption(
        '--mssql_username',
        action='store',
        dest='mssql_username',
        default='',
        help='Username for SQL Server. Do not use for Win authentication.'
        )
    parser.addoption(
        '--mssql_password',
        action='store',
        dest='mssql_password',
        default='',
        help='Password for SQL Server. Do not use for Win authentication.'
        )


pytest_plugins = [
    "test.operations.tsql.fixtures"
    ]


def pytest_configure(config):
    config.addinivalue_line("markers", "tsql: mark tests that require SQL server to run")


def pytest_collection_modifyitems(config, items):
    """First, check if tsql tests can be executed, that is,
        - MSSQL hostname was given
        - connection to MSSQL can be established using the
            given hostname, port number and credentials
        - MSSQL doesn't have database with name 'AHJO_TEST'

    If tsql tests can be executed, add fixture 'tsql_setup_and_teardown'
    to all tests marked with 'tsql'.

    If tsql tests can not be executed, skip tests marked with 'tsql'.
    """
    execute_tsql_tests = ensure_mssql_ready_for_tests(config)
    skip_tsql = pytest.mark.skip(reason="requires SQL Server")
    for item in items:
        if "tsql" in item.keywords:
            if execute_tsql_tests:
                item.fixturenames.append('tsql_setup_and_teardown')
            else:
                item.add_marker(skip_tsql)


def ensure_mssql_ready_for_tests(config):
    """Test connection to MSSQL instance
    and check the existence of database AHJO_TEST.
    """
    try:
        if not config.getoption('mssql_host'):
            raise Exception('MSSQL Server not given')
        connection_url = URL(
            drivername="mssql+pyodbc",
            username=config.getoption('mssql_username'),
            password=config.getoption('mssql_password'),
            host=config.getoption('mssql_host'),
            port=config.getoption('mssql_port'),
            database='master',
            query={'driver': 'SQL Server'}
        )
        engine = create_engine(connection_url)
        with engine.connect() as connection:
            query = "SELECT name FROM sys.databases WHERE UPPER(name) = 'AHJO_TEST'"
            result = connection.execute(query)
            if result.fetchall():
                raise Exception("There already exists a database with name 'AHJO_TEST'")
        return True
    except:
        return False
