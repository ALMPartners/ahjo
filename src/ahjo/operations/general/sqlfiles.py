# Ahjo - Database deployment framework
#
# Copyright 2019, 2020, 2021 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

"""Module for SQL script file deploy and drop."""
from collections import defaultdict
from logging import getLogger
from os import listdir, path
from pathlib import Path
from typing import Any, Callable, Union

from ahjo.database_utilities import execute_from_file, execute_try_catch
from ahjo.interface_methods import format_to_table
from ahjo.operation_manager import OperationManager
from sqlalchemy.engine import Engine

logger = getLogger('ahjo')


def deploy_sqlfiles(engine: Engine, directory: str, message: str, display_output: bool = False, variables: Union[list, tuple] = None) -> bool:
    """Run every SQL script file found in given directory and print the executed file names.

    If any file in directory cannot be deployed after multiple tries, raise an exeption and
    list failed files to user.

    Parameters
    ----------
    engine
        SQL Alchemy engine.
    directory
        Path of directory holding the SQL script files.
    message
        Message passed to OperationManager.
    display_output
        Indicator to print script output.
    variables
        Variables passed to SQL script.

    Raises
    ------
    ValueError
        If engine is not instance of sqlalchemy.engine.Engine.
    RuntimeError
        If any of the files in given directory fail to deploy after multiple tries.
    """
    with OperationManager(message):
        if isinstance(engine, dict):
            raise ValueError(
                "First parameter of function 'deploy_sqlfiles' should be instance of sqlalchemy engine. Check your custom actions!")
        if not Path(directory).is_dir():
            logger.warning("Directory not found: " + directory)
            return False
        files = [path.join(directory, f)
                 for f in listdir(directory) if f.endswith('.sql')]
        failed = sql_file_loop(deploy_sql_from_file, engine,
                               display_output, variables, file_list=files, max_loop=len(files))
        if len(failed) > 0:
            error_msg = "Failed to deploy the following files:\n{}".format(
                '\n'.join(failed.keys()))
            error_msg = error_msg + '\nSee log for error details.'
            for fail_object, fail_messages in failed.items():
                logger.debug(f'----- Error for object {fail_object} -----')
                logger.debug(''.join(fail_messages))
            raise RuntimeError(error_msg)
        return True


def drop_sqlfile_objects(engine: Engine, object_type: str, directory: str, message: str):
    """Drop all the objects created in SQL script files of an directory.

    The naming of the files should be consistent!

    Parameters
    ----------
    engine
        SQL Alchemy engine.
    object_type
        Type of database object.
    directory
        Path of directory holding the SQL script files.
    message
        Message passed to OperationManager.

    Raises
    ------
    RuntimeError
        If any of the files in given directory fail to drop after multiple tries.
    """
    with OperationManager(message):
        if not Path(directory).is_dir():
            logger.warning("Directory not found: " + directory)
            return
        files = [path.join(directory, f)
                 for f in listdir(directory) if f.endswith('.sql')]
        failed = sql_file_loop(drop_sql_from_file, engine,
                               object_type, file_list=files, max_loop=len(files))
        if len(failed) > 0:
            error_msg = "Failed to drop the following files:\n{}".format(
                '\n'.join(failed.keys()))
            for fail_messages in failed.values():
                error_msg = error_msg + ''.join(fail_messages)
            raise RuntimeError(error_msg)


def deploy_sql_from_file(file: str, engine: Engine, display_output: bool, variables: Union[list, tuple]):
    '''Run single SQL script file.

    Print output as formatted table.

    Parameters
    ----------
    file
        SQL script file path passed to SQLCMD.
    engine
        SQL Alchemy engine.
    display_output
        Indicator to print script output.
    variables
        Variables passed to SQL script.
    '''
    output = execute_from_file(engine, file_path=file, variables=variables, include_headers=True)
    logger.info(path.basename(file))
    if display_output:
        logger.info(format_to_table(output))


def drop_sql_from_file(file: str, engine: Engine, object_type: str):
    '''Run DROP OBJECT command for object in SQL script file.

    The drop command is based on object type and file name.

    Parameters
    ----------
    file
        SQL script file path.
    engine
        SQL Alchemy engine.
    object_type
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
    query = f"DROP {object_type} {object_name}"
    execute_try_catch(engine, query=query)


def sql_file_loop(command: Callable[..., Any], *args : Any, file_list: list, max_loop: int = 10) -> dict:
    '''Loop copy of file_list maximum max_loop times and execute the command to every file in
    copy of file_list. If command succeeds, drop the the file from copy of file_list. If command
    fails, keep the file in copy of file_list and execute the command again in next loop.

    When max_loop is reached and there are files in copy of file_list, return the remaining
    file names and related errors that surfaced during executions. Else return empty dict.

    Parameters
    ----------
    command
        Function to be executed to every file in file_list.
    *args
        Arguments passed to command.
    file_list
        List of file paths.
    max_loop
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
