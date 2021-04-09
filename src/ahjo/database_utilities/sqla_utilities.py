# Ahjo - Database deployment framework
#
# Copyright 2019, 2020, 2021 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

"""Utility functions for sqlalchemy
"""
from typing import Iterable, List, Union

from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import Engine
from sqlalchemy.engine.url import URL
from sqlalchemy.sql import text

MASTER_DB = {'mssql+pyodbc': 'master', 'postgresql': 'postgres'}
BATCH_SEPARATOR = {'mssql': '\nGO', 'postgresql': ';\n'}
SCRIPT_VARIABLE_PATTERN = {'mssql': '$({})', 'postgresql': ':{}'}


def create_sqlalchemy_url(conn_info: dict, use_master_db: bool = False) -> URL:
    """Create url for sqlalchemy/alembic.
    If use_master_db flag is on, pass 'master' database to url.

    Arguments
    ---------
    conn_info
        Dictionary holding information needed to establish database connection.
    use_master_db
        Indicator to connect to 'master' database.

    Returns
    -------
    sqlalchemy.engine.url.URL
        Connection url for sqlalchemy/alembic.
    """
    if use_master_db is True:
        database = MASTER_DB.get(conn_info.get('dialect'))
    else:
        database = conn_info.get('database')
    query = {}
    # Add optional driver to query-dictionary
    if conn_info.get('driver') is not None:
        query['driver'] = conn_info.get('driver')
    # sqlalchemy does not have full url support for different Azure authentications
    # ODBC connection string must be added to query
    azure_auth = conn_info.get('azure_auth')
    if azure_auth is not None:
        odbc = ''
        if azure_auth.lower() == 'activedirectorypassword':
            authentication = 'ActiveDirectoryPassword'
            odbc = f"Pwd{{{conn_info.get('password')}}};"
        elif azure_auth.lower() == 'activedirectoryintegrated':
            authentication = 'ActiveDirectoryIntegrated'
        elif azure_auth.lower() == 'activedirectoryinteractive':
            authentication = 'ActiveDirectoryInteractive'
        else:
            raise Exception(
                "Unknown Azure authentication type! Check variable 'azure_authentication'.")
        query['odbc_connect'] = odbc + "Driver={{{driver}}};Server={server};Database={database};Uid={{{uid}}};Encrypt=yes;TrustServerCertificate=no;Authentication={auth}".format(
            driver=conn_info.get('driver'),
            server=conn_info.get('server'),
            database=database,
            uid=conn_info.get('username'),
            auth=authentication
        )
    return URL(
        drivername=conn_info.get('dialect'),
        username=conn_info.get('username'),
        password=conn_info.get('password'),
        host=conn_info.get('host'),
        port=conn_info.get('port'),
        database=database,
        query=query
    )


def create_sqlalchemy_engine(sqlalchemy_url: URL, **kwargs) -> Engine:
    """Create a new SQL Alchemy engine.

    Arguments
    ---------
    sqlalchemy_url
        Connection url for sqlalchemy/alembic.
    kwargs
        Named arguments passed to create_engine().

    Returns
    -------
    sqlalchemy.engine.Engine
        SQL Alchemy engine.
    """
    engine = create_engine(sqlalchemy_url, **kwargs)
    return engine


def execute_query(engine: Engine, query: str, variables: Union[list, tuple] = None, isolation_level: str = 'AUTOCOMMIT', include_headers: bool = False) -> List[Iterable]:
    """Execute query with chosen isolation level.

    Arguments
    ---------
    engine
        SQL Alchemy engine.
    query
        SQL query or statement to be executed.
    variables
        Variables for query.
    isolation_level
        Transaction isolation level.
        See https://docs.sqlalchemy.org/en/13/core/connections.html#sqlalchemy.engine.Connection.execution_options.params.isolation_level
    include_headers
        Indicator to add result headers to first returned row.

    Returns
    -------
    list
        Query output as list. If query returns no output, empty list is returned.
    """
    with engine.connect() as connection:
        connection.execution_options(isolation_level=isolation_level)
        if variables is not None and isinstance(variables, (tuple, list)):
            result_set = connection.execute(query, *variables)
        else:
            result_set = connection.execute(query)
        query_output = []
        if result_set.returns_rows:
            if include_headers is True:
                query_output.append(list(result_set.keys()))
            query_output.extend([row for row in result_set])
        return query_output


def execute_try_catch(engine: Engine, query: str, variables: Union[list, tuple] = None, throw: bool = False):
    """Execute query with try catch.
    If throw is set to True, raise error in case query execution fails.

    Arguments
    ---------
    engine
        SQL Alchemy engine.
    query
        SQL query or statement to be executed.
    variables
        Variables for query.
    throw
        Indicator to raise error if query execution fails.
    """
    with engine.connect() as connection:
        trans = connection.begin()
        try:
            if variables is not None and isinstance(variables, (tuple, list)):
                connection.execute(query, *variables)
            else:
                connection.execute(query)
            trans.commit()
        except:
            trans.rollback()
            if throw is True:
                raise


def execute_from_file(engine: Engine, file_path: str, scripting_variables: dict = None, include_headers: bool = False) -> List[Iterable]:
    """Open file containing raw SQL and execute in batches.
    File is expected to be UTF-8 or UTF-8 with BOM.

    Batches are split using the batch separator, which is defined by used dialect.

    Arguments
    ---------
    engine
        SQL Alchemy engine.
    file_path
        Full path to SQL script file.
    scripting_variables
        Variables that are used in scripts. Works in similar manner as scripting variables in SQLCMD.
        Notice, that variable values are inserted into raw SQL before execute and are not escaped!
        Therefore these can be utilized in SQL injection attack. USE CAREFULLY!
    include_headers
        Indicator to add result headers to first returned row.

    Returns
    -------
    list
        Query output as list. If query returns no output, empty list is returned.
    """
    # TODO: encoding varoitus
    with open(file_path, 'r', encoding='utf-8-sig') as f:
        sql = f.read()
    if scripting_variables:
        for variable_name, variable_value in scripting_variables.items():
            pattern = SCRIPT_VARIABLE_PATTERN.get(engine.name, '{}')
            sql = sql.replace(pattern.format(variable_name), variable_value)
    batch_separator = BATCH_SEPARATOR.get(engine.name)
    if batch_separator:
        batches = sql.split(batch_separator)
    else:
        batches = [sql]
    with engine.connect() as connection:
        connection.execution_options(isolation_level='AUTOCOMMIT')
        script_output = []
        for batch in batches:
            if not batch:
                continue
            result_set = connection.execute(text(batch))
            if result_set.returns_rows:
                if script_output == [] and include_headers is True:
                    script_output.append(list(result_set.keys()))
                script_output.extend([row for row in result_set])
    return script_output


def get_schema_names(engine: Engine) -> List[str]:
    """Return schema names from database."""
    inspector = inspect(engine)
    db_list = inspector.get_schema_names()
    return db_list
