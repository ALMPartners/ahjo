# Ahjo - Database deployment framework
#
# Copyright 2019, 2020, 2021 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

"""Utility functions for executing tsql using sqlcmd.exe
"""
from collections import defaultdict
from logging import getLogger
from os import path
from re import search
from subprocess import PIPE, Popen, list2cmdline

from ahjo.database_utilities.sqla_utilities import execute_try_catch

logger = getLogger('ahjo')


def invoke_sqlcmd(conn_info, infile=None, query=None, variable=None):
    """Runs a t-sql script or query using sqlcmd.exe
    Prints sql-errors and returns the standard output.

    Arguments
    ---------
    infile: str
        The input file path, from which the sqlcmd reads the queries.
        Alternative to query string passing (next argument).
    query: str
        The sql query as a string.
        Alternative to input-file query passing.
    variable: list of str or str
        Variables for the sqlcmd query.
        Takes a list of strings or a string.
    """
    subprocess_args = ["sqlcmd.exe"]
    server = conn_info.get('server')
    database = conn_info.get('database')
    username = conn_info.get('username')
    password = conn_info.get('password')
    subprocess_args += ["-S", server]
    if database is not None:
        subprocess_args += ["-d", str(database)]
    if username is not "" and password is not "":
        subprocess_args += ["-U", username, "-P", str(password)]
    else:
        subprocess_args += ["-E"]  # trusted connection
    if infile is not None:
        subprocess_args += ["-i", infile]
    if query is not None:
        subprocess_args += ["-Q", query]
    subprocess_args += ['-h-1']  # rows per header
    subprocess_args += ["-r0"]  # sql errors to error output
    subprocess_args += ["-f", "65001"]  # codepage UTF-8
    # variables can be given as string or list
    # DP-68: In cases where variable includes colon or spaces,
    # the variable needs to be closes with double quotes.
    # DB_PATH="'C:\temp\crdm\data\DB.mdf'"
    if variable is not None:
        if isinstance(variable, str):
            subprocess_args += ["-v", variable]
        elif isinstance(variable, list):
            for var in variable:
                subprocess_args += ["-v", var] if var is not None else []
        argument_str = list2cmdline(subprocess_args)
        subprocess_args = _add_cmdline_quotes(argument_str)

    # subprocess call with a separate error-output
    command_process = Popen(subprocess_args, stdout=PIPE, stderr=PIPE)
    output, error = command_process.communicate()
    if len(error) > 0:
        error_msg = error.decode("utf-8").strip()
        if query is not None:
            if len(query) > 100:
                error_msg = error_msg + '\nQuery: "' + query[:100] + '..."'
            else:
                error_msg = error_msg + '\nQuery: "' + query + '"'
        if infile is not None:
            error_msg = error_msg + '\nFile: ' + infile
        raise RuntimeError(error_msg)
    return output


def deploy_tsql_from_file(file, conn_info, display_output, variable):
    '''Run single TSQL script file.

    Parameters
    ----------
    file : str
        SQL script file path passed to SQLCMD.
    conn_info : dict
        Dictionary holding information needed to establish database connection.
    display_output : bool
        Indicator to print script output.
    '''
    output = invoke_sqlcmd(conn_info, infile=file, variable=variable)
    logger.info(path.basename(file))
    if display_output:
        logger.info(output.decode('utf-8'))


def drop_tsql_from_file(file, engine, object_type):
    '''Run DROP OBJECT command for object in SQL script file.

    The drop command is based on object type and file name.

    Parameters
    ----------
    file : str
        SQL script file path.
    engine : sqlalchemy.engine.Engine
        SQL Alchemy engine.
    object_type : str
        Type of database object.
    '''
    parts = path.basename(file).split('.')
    # SQL files are assumed to be named in format: schema.object.sql
    # The only exception is assemblies. Assemblies don't have schema.
    if object_type == 'ASSEMBLY':
        object_name = parts[0]
    else:
        if len(parts) != 3:
            raise RuntimeError(f'File {file} not in <schema.object.sql> format.')
        object_name = parts[0] + '.' + parts[1]
    query = f"BEGIN TRY DROP {object_type} {object_name} END TRY BEGIN CATCH END CATCH"
    execute_try_catch(engine, query=query)


def sql_file_loop(command, *args, file_list, max_loop=10):
    '''Loop copy of file_list maximum max_loop times and execute the command to every file in
    copy of file_list. If command succeeds, drop the the file from copy of file_list. If command
    fails, keep the file in copy of file_list and execute the command again in next loop.

    When max_loop is reached and there are files in copy of file_list, return the remaining
    file names and related errors that surfaced during executions. Else return empty dict.

    Parameters
    ----------
    command : function
        Command to be executed to every file in file_list.
    *args
        Arguments passed to command.
    file_list : list
        List of file paths.
    max_loop : int
        Maximum number of loops.

    Returns
    -------
    dict
        Failed files and related errors. Empty if no fails.
    '''
    copy_list = file_list.copy()
    copy_list_loop = copy_list.copy()
    errors = defaultdict(set)
    for _ in range(max_loop):
        for file in copy_list_loop:
            try:
                command(file, *args)
                copy_list.remove(file)
            except Exception as error:
                error_str = '\n------\n' + str(error)
                errors[file].add(error_str)
        copy_list_loop = copy_list.copy()
    if len(copy_list) > 0:
        return {f: list(errors[f]) for f in copy_list}
    return {}


def _add_cmdline_quotes(cmd_str):
    """Add extra quotes to command line string containing SQL variables.

    DB_PATH='C:\\temp\\crdm\\data\\BD:mdf' => DB_PATH="'C:\\temp\\crdm\\data\\BD:mdf'"

    Arguments
    ---------
    cmd_str : str
        Command line string containing SQL variables.

    Returns
    -------
    cmd_str : str
        Command line string with extra quotes.
    """
    match = search("='[^']*'", cmd_str)
    if match is not None:
        quoted_cmd_str = cmd_str[:match.start() + 1] + '"' + cmd_str[match.start() + 1: match.end()] + '"' + cmd_str[match.end():]
        cmd_str = _add_cmdline_quotes(quoted_cmd_str)
    return cmd_str
