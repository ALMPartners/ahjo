# Ahjo - Database deployment framework
#
# Copyright 2019 - 2023 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

"""Utility functions for sqlalchemy
"""
from ahjo.interface_methods import rearrange_params
from logging import getLogger
from os import path
from re import DOTALL, sub
from typing import Iterable, List, Union
from traceback import format_exc

from pyparsing import (Combine, LineStart, Literal, QuotedString, Regex,
                       restOfLine, CaselessKeyword, Word, nums)
from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import Engine, Connection
from sqlalchemy.engine.url import URL
from sqlalchemy.sql import text
from sqlalchemy import event
from sqlalchemy.orm import Session

logger = getLogger('ahjo')
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
    azure_auth = conn_info.get('azure_auth')
    driver = conn_info.get('driver')
    server = conn_info.get('server')
    username = conn_info.get('username')
    password = conn_info.get('password')
    dialect = conn_info.get('dialect')
    host = conn_info.get('host')
    port = conn_info.get('port')
    odbc_trust_server_certificate = conn_info.get('odbc_trust_server_certificate', 'no')
    odbc_encrypt = conn_info.get('odbc_encrypt', 'yes')

    if use_master_db is True:
        database = MASTER_DB.get(dialect)
    else:
        database = conn_info.get('database')
    query = {}
    # Add optional driver to query-dictionary
    if driver is not None:
        query['driver'] = driver
    
    # sqlalchemy does not have full url support for different Azure authentications
    # ODBC connection string must be added to query
    if azure_auth is not None:

        odbc = ''
        azure_auth_lower = azure_auth.lower()
        
        if azure_auth_lower == 'activedirectorypassword':
            authentication = 'ActiveDirectoryPassword'
            odbc = f"Pwd{{{password}}};"
        elif azure_auth_lower == 'activedirectoryintegrated':
            authentication = 'ActiveDirectoryIntegrated'
        elif azure_auth_lower == 'activedirectoryinteractive':
            authentication = 'ActiveDirectoryInteractive'
        elif azure_auth_lower == 'azureidentity':
            authentication = 'AzureIdentity'
        else:
            raise Exception(
                "Unknown Azure authentication type! Check variable 'azure_authentication'.")

        if azure_auth_lower != 'azureidentity':
            query['odbc_connect'] = odbc + "Driver={{{driver}}};Server={server};Database={database};Uid={{{uid}}};Encrypt={odbc_encrypt};TrustServerCertificate={odbc_trust_server_certificate};Authentication={auth}".format(
                driver = driver,
                server = server,
                database = database,
                uid = username,
                odbc_encrypt = odbc_encrypt,
                odbc_trust_server_certificate = odbc_trust_server_certificate,
                auth = authentication
            )
        else:
            query['odbc_connect'] = "Driver={{{driver}}};Server={server};Database={database};Encrypt={odbc_encrypt};TrustServerCertificate={odbc_trust_server_certificate};".format(
                driver = driver,
                server = server,
                database = database,
                odbc_encrypt = odbc_encrypt,
                odbc_trust_server_certificate = odbc_trust_server_certificate
            )
            return URL.create(
                drivername = dialect,
                host = host,
                port = port,
                database = database,
                query = query
            )

    # Specific parameters for ODBC Driver 18.0 for SQL Server
    # More info: https://techcommunity.microsoft.com/t5/sql-server-blog/odbc-driver-18-0-for-sql-server-released/ba-p/3169228
    if driver.lower() == "odbc driver 18 for sql server":
        query["TrustServerCertificate"] = odbc_trust_server_certificate
        query["Encrypt"] = odbc_encrypt

    return URL.create(
        drivername = dialect,
        username = username,
        password = password,
        host = host,
        port = port,
        database = database,
        query=query
    )
    


def create_sqlalchemy_engine(sqlalchemy_url: URL, token: bytes = None, **kwargs) -> Engine:
    """Create a new SQL Alchemy engine.

    Arguments
    ---------
    sqlalchemy_url
        Connection url for sqlalchemy/alembic.
    token
        Dynamic authentication token (optional)
    kwargs
        Named arguments passed to create_engine().

    Returns
    -------
    sqlalchemy.engine.Engine
        SQL Alchemy engine.
    """
    if sqlalchemy_url.get_dialect().name == "mssql" and sqlalchemy_url.get_driver_name() == "pyodbc":
        engine = create_engine(
            sqlalchemy_url, 
            use_insertmanyvalues=False, 
            use_setinputsizes=False, 
            **kwargs
        )
    else:
        engine = create_engine(sqlalchemy_url, **kwargs)        
    if token is not None:
        @event.listens_for(engine, "do_connect")
        def provide_token(dialect, conn_rec, cargs, cparams):
            SQL_COPT_SS_ACCESS_TOKEN = 1256  # Connection option for access tokens, as defined in msodbcsql.h
            cargs[0] = cargs[0].replace(";Trusted_Connection=Yes", "") # remove the "Trusted_Connection" parameter that SQLAlchemy adds
            cparams["attrs_before"] = {SQL_COPT_SS_ACCESS_TOKEN: token} # apply it to keyword arguments
    return engine


@rearrange_params({"engine": "connectable"})
def execute_query(connectable: Union[Engine, Connection, Session], query: str, variables: Union[dict, list, tuple] = None, 
        isolation_level: str = 'AUTOCOMMIT', include_headers: bool = False) -> List[Iterable]:
    """Execute query with chosen isolation level.

    Arguments
    ---------
    connectable
        SQL Alchemy Engine, Connection or Session.
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
    if type(connectable) == Engine: 
        connection_obj = connectable.connect()
        connection_obj.execution_options(isolation_level=isolation_level)
    else:
        connection_obj = connectable
    
    if variables is not None and isinstance(variables, (dict, list, tuple)):
        if isinstance(variables, (list, tuple)):
            query, variables = _create_sql_construct(query, variables)
        result_set = connection_obj.execute(text(query), variables)
    else:
        result_set = connection_obj.execute(text(query)) if isinstance(query, str) else connection_obj.execute(query)
    query_output = []
    if result_set.returns_rows:
        if include_headers is True:
            query_output.append(list(result_set.keys()))
        query_output.extend([row for row in result_set])
    if type(connectable) == Engine: 
        connection_obj.commit()
        connection_obj.close()
    return query_output


def execute_try_catch(engine: Engine, query: str, variables: dict = None, throw: bool = False):
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
            if variables is not None and isinstance(variables, (dict, list, tuple)):
                if isinstance(variables, (list, tuple)): 
                    query, variables = _create_sql_construct(query, variables)
                connection.execute(text(query), variables)
            else:
                connection.execute(text(query)) if isinstance(query, str) else connection.execute(query)
            trans.commit()
        except:
            trans.rollback()
            if throw is True:
                raise


@rearrange_params({"engine": "connectable"})
def execute_files_in_transaction(connectable: Union[Engine, Connection, Session], files: list, scripting_variables: dict = None, 
        include_headers: bool = False, commit_transaction: bool = True) -> List[Iterable]:
    """Execute SQL scripts from list of files in transaction. 
    Rollback if any of the batches fail.
    
    Arguments
    ---------
    connectable
        SQL Alchemy Engine, Connection or Session.
    files
        List of files to be executed.
    scripting_variables
        Variables for SQL scripts.
    include_headers
        Indicator to add result headers to first returned row.
    commit_transaction
        Indicator to commit transaction after execution.
        Parameter is ignored if connectable is Engine.
    """
    script_output = []
    dialect_name = get_dialect_name(connectable)
    connectable_type = type(connectable)
    connection_obj = connectable.connect() if connectable_type == Engine else connectable
    succeeded_files = []
    errors = {}
    n_files = len(files)
    loop_files = files.copy()
    looped_files = set()
    try:
        for _ in range(n_files):
            for file in loop_files:
                if file not in looped_files: logger.info(path.basename(file))
                looped_files.add(file)
                batches = _file_to_batches(dialect_name, file, scripting_variables)
                try:
                    results = _execute_batches(connection_obj, batches, include_headers=include_headers, commit_transaction=False, rollback_on_error=False)
                except:
                    errors[file] = '\n------\n' + format_exc()
                    continue
                else:
                    succeeded_files.append(file)
                    script_output.append(results)
                    loop_files.remove(file)
                    errors.pop(file, None)
            if n_files == len(succeeded_files):
                break
        if n_files != len(succeeded_files):
            error_msg = "Failed to deploy files."
            error_msg = error_msg + '\nSee log for error details.'
            for fail_object, fail_messages in errors.items():
                logger.debug(f'----- Error for object {fail_object} -----')
                logger.debug(''.join(fail_messages))
            raise Exception(error_msg)
    except:
        connection_obj.rollback()
        connection_obj.close()
        raise
    if commit_transaction is True or connectable_type == Engine:
        connection_obj.commit()

    return script_output


def drop_files_in_transaction(connection: Connection, drop_queries: dict) -> List[Iterable]:
    """Drop SQL scripts from list of files in transaction. 
    Rollback if any of the batches fail.
    
    Arguments
    ---------
    connection
        SQL Alchemy Connection.
    drop_queries
        Dictionary of files and drop queries.
    """
    script_output = []
    files = drop_queries.keys()
    try:
        for file in files:
            logger.info(path.basename(file))
            results = execute_query(connection, query = drop_queries[file])
            script_output.append(results)
    except:
        connection.rollback()
        connection.close()
        raise
    return script_output


@rearrange_params({"engine": "connectable"})
def execute_from_file(connectable: Union[Engine, Connection, Session], file_path: str, scripting_variables: dict = None, include_headers: bool = False, 
        file_transaction: bool = False, commit_transaction: bool = False) -> List[Iterable]:
    """Open file containing raw SQL and execute in batches.
    File is must be UTF-8 or UTF-8 with BOM.

    Batches are split using a dialect dependent batch separator.

    Arguments
    ---------
    connectable
        SQL Alchemy Engine, Connection or Session.
    file_path
        Full path to SQL script file.
    scripting_variables
        Variables that are used in scripts.
        Works in a similar manner as scripting variables in SQLCMD.

        **WARNING** variable values are inserted without escaping into raw SQL before execute!
        Therefore scripting variables can be utilized in SQL injection attack. USE CAREFULLY!
    include_headers
        Indicator to add result headers to first returned row.
    file_transaction
        Indicator to execute file in transaction. Default is False.
    commit_transaction
        Indicator to commit transaction after script execution. Default is True.
        Parameter is ignored if connectable is Engine.

    Returns
    -------
    list
        Query output as list. If query returns no output, empty list is returned.
    """
    
    connectable_type = type(connectable)
    if connectable_type == Engine:
        connection_obj = connectable.connect()
        if not file_transaction:
            connection_obj.execution_options(isolation_level='AUTOCOMMIT')
    else:
        connection_obj = connectable

    dialect_name = get_dialect_name(connectable)
    batches = _file_to_batches(dialect_name, file_path, scripting_variables)
    script_output = []

    if file_transaction:
        try:
            script_output = _execute_batches(connection_obj, batches, include_headers=include_headers, commit_transaction=False)
        except:
            connection_obj.rollback()
            connection_obj.close()
            raise
        if commit_transaction or connectable_type == Engine:
            connection_obj.commit()
    else:
        script_output = _execute_batches(connection_obj, batches, include_headers=include_headers, commit_transaction=commit_transaction)

    if connectable_type == Engine:
        connection_obj.close()

    return script_output


def _file_to_batches(dialect_name, file_path, scripting_variables):
    """Open file containing raw SQL and split into batches."""
    try:
        with open(file_path, 'r', encoding='utf-8-sig', errors='strict') as f:
            sql = f.read()
    except ValueError as err:
        raise ValueError(f'File {file_path} is not UTF-8 or UTF-8 BOM encoded!') from err
    
    dialect = get_dialect_patterns(dialect_name)
    if scripting_variables:
        sql = _insert_script_variables(dialect, sql, scripting_variables)

    return _split_to_batches(dialect, sql)


@rearrange_params({"engine": "connectable"})
def _execute_batches(connectable: Union[Connection, Session], batches: list, include_headers: bool = False, 
        commit_transaction: bool = True, rollback_on_error: bool = True):
    """Execute batches of SQL statements."""
    connectable_type = type(connectable)
    script_output = []
    for batch in batches:

        if not batch:
            continue
        batch = sub(':', r'\:', batch)

        if connectable_type == Session or connectable_type == Connection:
            try:
                script_output = _execute_batch(connectable, batch, script_output, include_headers = include_headers)
            except:
                if rollback_on_error: 
                    connectable.rollback()
                    connectable.close()
                raise
            if commit_transaction:
                connectable.commit()
        else:
            script_output = _execute_batch(connectable, batch, script_output, include_headers = include_headers)

    return script_output


@rearrange_params({"engine": "connectable"})
def _execute_batch(connectable: Union[Connection, Session], batch: str, script_output: list, include_headers: bool = False):
    """Execute batch of SQL statements."""
    result_set = connectable.execute(text(batch))
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


def _create_sql_construct(query: str, variables: Union[list, tuple]):
    """Create a SQL statement construct. 
    Bind variables into SQL string from list/tuple."""
    variables_dict = {}
    for var in variables:
        bind_var = ":p_" + str(var)
        query = sub(r"\?", bind_var, query, count=1)
        variables_dict[bind_var[1:]] = var
    variables = variables_dict
    return query, variables


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

    # Override default behavior of converting tabs to spaces before parsing the input string
    sql_batch.parseWithTabs()
    
    scan_matches = list(sql_batch.scanString(sql))
    # if no batch separator instance found in SQL, return
    if not scan_matches:
        return [sql]
    batches = []
    for i, _ in enumerate(scan_matches):
        try:
            count = int(scan_matches[i][0][1])
        except IndexError:
            count = 1
        for _ in range(0, count):
            if i == 0:
                batches.append(sql[:scan_matches[i][1]])
            else:
                batches.append(sql[scan_matches[i-1][2]:scan_matches[i][1]])
    batches.append(sql[scan_matches[-1][2]:])
    
    return batches


@rearrange_params({"engine": "connectable"})
def get_dialect_name(connectable: Union[Engine, Connection, Session]) -> str:
    """Return dialect name from Engine, Connection or Session."""
    connectable_type = type(connectable)
    if connectable_type == Session:
        dialect_name = connectable.bind.dialect.name
    elif connectable_type == Connection:
        dialect_name = connectable.dialect.name
    else: # Engine
        dialect_name = connectable.name
    return dialect_name


@rearrange_params({"engine": "connectable"})
def get_schema_names(connectable: Union[Engine, Connection]) -> List[str]:
    """Return schema names from database."""
    inspector = inspect(connectable)
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
            'batch_separator': LineStart().leaveWhitespace() + ( ( CaselessKeyword('GO') + Word(nums) ) | CaselessKeyword('GO') ),
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
