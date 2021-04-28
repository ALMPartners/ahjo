# Ahjo - Database deployment framework
#
# Copyright 2019, 2020, 2021 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

"""Utility functions for sqlalchemy
"""
from re import DOTALL
from typing import Iterable, List, Union

from pyparsing import (Combine, LineStart, Literal, QuotedString, Regex,
                       restOfLine)
from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import Engine
from sqlalchemy.engine.url import URL
from sqlalchemy.sql import text

MASTER_DB = {'mssql+pyodbc': 'master', 'postgresql': 'postgres'}


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
    File is must be UTF-8 or UTF-8 with BOM.

    Batches are split using a dialect dependent batch separator.

    Arguments
    ---------
    engine
        SQL Alchemy engine.
    file_path
        Full path to SQL script file.
    scripting_variables
        Variables that are used in scripts.
        Works in a similar manner as scripting variables in SQLCMD.

        **WARNING** variable values are inserted without escaping into raw SQL before execute!
        Therefore scripting variables can be utilized in SQL injection attack. USE CAREFULLY!
    include_headers
        Indicator to add result headers to first returned row.

    Returns
    -------
    list
        Query output as list. If query returns no output, empty list is returned.
    """
    try:
        with open(file_path, 'r', encoding='utf-8-sig', errors='strict') as f:
            sql = f.read()
    except ValueError as err:
        raise ValueError(f'File {file_path} is not UTF-8 or UTF-8 BOM encoded!') from err
    dialect = get_dialect_patterns(engine.name)
    if scripting_variables:
        sql = _insert_script_variables(dialect, sql, scripting_variables)
    batches = _split_to_batches(dialect, sql)
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


def _insert_script_variables(dialect_patterns: dict, sql: str, scripting_variables: dict):
    """Insert scripting variables into SQL,
    use pattern according to dialect."""
    for variable_name, variable_value in scripting_variables.items():
        pattern = dialect_patterns.get('script_variable_pattern', '{}')
        sql = sql.replace(pattern.format(variable_name), variable_value)
    return sql


def _split_to_batches(dialect_patterns: dict, sql: str) -> List[str]:
    """Split SQL into batches according to batch separator,
    which depends on dialect. Ignore comments and literals while parsing.
    If no batch separator given or no batch separator instance
    found in SQL, do not split SQL.
    """
    batch_separator = dialect_patterns.get('batch_separator')
    one_line_comment = dialect_patterns.get('one_line_comment')
    multiline_comment = dialect_patterns.get('multiline_comment')
    quoted_strings = dialect_patterns.get('quoted_strings')
    # if no batch separator given, return
    if not batch_separator:
        return [sql]
    # look for batch separators while ignoring comments and literals
    sql_batch = batch_separator
    if one_line_comment:
        sql_batch.ignore(one_line_comment)
    if multiline_comment:
        sql_batch.ignore(multiline_comment)
    for quote_str in quoted_strings:
        sql_batch.ignore(quote_str)

    # Pyparsing implicitly calls str.expandtabs before running its parse/scan methods
    sql = sql.expandtabs()
    found_separators = sql_batch.scanString(sql)
    sep_indexes = [(start, end) for _, start, end in found_separators]
    # if no batch separator instance found in SQL, return
    if not sep_indexes:
        return [sql]
    batches = []
    for i, _ in enumerate(sep_indexes):
        if i == 0:
            batches.append(sql[:sep_indexes[i][0]])
        else:
            batches.append(sql[sep_indexes[i-1][1]:sep_indexes[i][0]])
    batches.append(sql[sep_indexes[-1][1]:])
    return batches


def get_schema_names(engine: Engine) -> List[str]:
    """Return schema names from database."""
    inspector = inspect(engine)
    db_list = inspector.get_schema_names()
    return db_list


def get_dialect_patterns(dialect_name: str) -> dict:
    """Return dialect patterns (used in SQL parsing), given dialect name.
    If dialect name not recorded, return empty dictionary.
    """
    # Notice, that if DIALECT_PATTERS is a global variable, pyparsing slows down remarkably.
    DIALECT_PATTERNS = {
        'mssql': {
            'quoted_strings': [    # depends on how QUOTED_IDENTIFIER is set
                QuotedString("'", escQuote="''", multiline=True),
                QuotedString('"', escQuote='""', multiline=True)
            ],
            'one_line_comment': Combine('--' + restOfLine),
            'multiline_comment': Regex(r'/\*.+?\*/', flags=DOTALL),
            # GO must be on its own line
            # TODO: GO with count
            'batch_separator': Combine(LineStart() + Literal('GO')),
            'script_variable_pattern': '$({})'
        },
        'postgresql': {    # https://www.postgresql.org/docs/current/sql-syntax-lexical.html
            'quoted_strings': [
                QuotedString("'", escQuote="''", multiline=True),
                QuotedString('$$', multiline=True)    # TODO: dollar quote with tag
            ],
            'one_line_comment': Combine('--' + restOfLine),
            'multiline_comment': Regex(r'/\*.+?\*/', flags=DOTALL),
            'batch_separator': Literal(';'),
            'script_variable_pattern': ':{}'
        },
        'sqlite': {    # https://sqlite.org/lang.html
            'quoted_strings': [QuotedString("'", escQuote="''", multiline=True)],
            'one_line_comment': Combine('--' + restOfLine),
            'multiline_comment': Regex(r'/\*.+?\*/', flags=DOTALL),
            'batch_separator': Literal(';')
        }
    }
    return DIALECT_PATTERNS.get(dialect_name, {})
