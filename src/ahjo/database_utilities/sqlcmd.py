# Ahjo - Database deployment framework
#
# Copyright 2019, 2020, 2021 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

"""Utility functions for executing tsql using sqlcmd.exe
"""
from logging import getLogger
from re import search
from subprocess import PIPE, Popen, list2cmdline
from typing import Union

logger = getLogger('ahjo')


def invoke_sqlcmd(conn_info: dict, infile: str = None, query: str = None, variable: Union[str, list] = None) -> bytes:
    """Runs a t-sql script or query using sqlcmd.exe
    Prints sql-errors and returns the standard output.

    Arguments
    ---------
    conn_info
        Dictionary holding information needed to establish database connection.
    infile
        The input file path, from which the sqlcmd reads the queries.
        Alternative to query string passing (next argument).
    query
        The sql query as a string.
        Alternative to input-file query passing.
    variable
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
    if username != "" and password != "":
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


def _add_cmdline_quotes(cmd_str: str) -> str:
    """Add extra quotes to command line string containing SQL variables.

    DB_PATH='C:\\temp\\crdm\\data\\BD:mdf' => DB_PATH="'C:\\temp\\crdm\\data\\BD:mdf'"

    Arguments
    ---------
    cmd_str
        Command line string containing SQL variables.

    Returns
    -------
    str
        Command line string with extra quotes.
    """
    match = search("='[^']*'", cmd_str)
    if match is not None:
        quoted_cmd_str = cmd_str[:match.start(
        ) + 1] + '"' + cmd_str[match.start() + 1: match.end()] + '"' + cmd_str[match.end():]
        cmd_str = _add_cmdline_quotes(quoted_cmd_str)
    return cmd_str
