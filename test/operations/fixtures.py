"""Fixtures related to operations."""
from base64 import b64encode
from distutils.dir_util import copy_tree
from os import path
from subprocess import PIPE, Popen

import commentjson as json
import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine.url import URL


@pytest.fixture(scope='session')
def mssql_engine(request, ahjo_config, mssql_sample):
    config = ahjo_config(mssql_sample)
    connection_url = URL(
        drivername="mssql+pyodbc",
        username=request.config.getoption('mssql_username'),
        password=request.config.getoption('mssql_password'),
        host=config['target_server_hostname'],
        port=config['sql_port'],
        database='master',
        query={'driver': 'SQL Server'}
    )
    return create_engine(connection_url)


@pytest.fixture(scope='session')
def mssql_setup_and_teardown(mssql_sample):
    """Copy MSSQL project to temporary dir.
    Rewrite configurations and create credential files.
    Init database for testing using Ahjo action 'init'.
    Execute mssql tests.
    Delete database using custom Ahjo action 'delete-database'.
    """
    p = Popen(['ahjo', 'init', 'config_development.jsonc'],
              cwd=mssql_sample, stdin=PIPE)
    p.communicate(input='y\n'.encode())
    yield
    p = Popen(['ahjo', 'delete-database', 'config_development.jsonc'],
              cwd=mssql_sample, stdin=PIPE)
    p.communicate(input='y\n'.encode())
