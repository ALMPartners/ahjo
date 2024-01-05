# Ahjo - Database deployment framework
#
# Copyright 2019 - 2023 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

"""Module for SQL script file deploy and drop."""
from collections import defaultdict
from logging import getLogger
from os import listdir, path
from pathlib import Path
from traceback import format_exc
from typing import Any, Callable, Union

from ahjo.interface_methods import rearrange_params
from ahjo.database_utilities import execute_from_file, execute_try_catch, execute_files_in_transaction, drop_files_in_transaction
from ahjo.interface_methods import format_to_table
from ahjo.operation_manager import OperationManager
from sqlalchemy.engine import Engine, Connection
from sqlalchemy.orm import Session

logger = getLogger('ahjo')

def sql_files_found(data_src):
    files = []
    if isinstance(data_src, str) and len(data_src) > 0:
        if not Path(data_src).is_dir():
            logger.warning("Directory not found: " + data_src)
            return files
        files = [path.join(data_src, f) for f in listdir(data_src) if f.endswith('.sql')]
    elif isinstance(data_src, list):
        invalid_params = []
        for arg in data_src:
            if arg.endswith('.sql'):
                files.append(arg)
            else:
                invalid_params.append(arg)
        if len(invalid_params) > 0:
            logger.warning("SQL file(s) not found from: " + ' '.join(invalid_params))
    else:
        logger.warning("Parameter 'data_src' should be non-empty string or list.")
    return files


@rearrange_params({"engine": "connectable"})
def deploy_sqlfiles(connectable: Union[Engine, Connection], data_src: Union[str, list], message: str, display_output: bool = False, 
        scripting_variables: dict = None, enable_transaction: bool = None, transaction_scope: str = None, commit_transaction: bool = False) -> bool:
    """Run every SQL script file found in given directory/filelist and print the executed file names.

    If any file in directory/filelist cannot be deployed after multiple tries, raise an exeption and
    list failed files to user.

    Parameters
    ----------
    connectable
        SQL Alchemy Engine or Connection.
    data_src
        If data_src is string: path of directory holding the SQL script files.
        If data_src is list: list of filepaths referencing to the SQL scripts.
    message
        Message passed to OperationManager.
    display_output
        Indicator to print script output.
    scripting_variables
        Variables passed to SQL script.
    enable_transaction
        Indicator to run script in transaction.
    transaction_scope
        Transaction scope for SQL script execution. 
        Possible values: 'files', 'file'.
        If 'files', all the files are executed in one transaction.
        If 'file', every file is executed in separate transaction.
        If None, transaction_scope is set to 'files' by default if connectable is not Engine.
        Used only if enable_transaction is True.
    commit_transaction
        Indicator to commit transaction after execution. Default is False.

    Raises
    ------
    ValueError
        If engine is not instance of sqlalchemy.engine.Engine.
    RuntimeError
        If any of the files in given directory/filelist fail to deploy.
    """
    with OperationManager(message):

        connectable_type = type(connectable)
        check_connectable_type(connectable, "deploy_sqlfiles")
        files = sql_files_found(data_src)
        n_files = len(files)
        error_msg = None
        if n_files == 0: return False

        # Set transaction scope to 'files' if not set by user and connectable is not Engine.
        transaction_scope = "files" if (enable_transaction is None and connectable_type is not Engine) else transaction_scope

        if transaction_scope != "files":
            failed = sql_file_loop(
                deploy_sql_from_file, 
                connectable,
                display_output, 
                scripting_variables, 
                True if enable_transaction and transaction_scope == "file" else False,
                True if connectable_type is Engine else commit_transaction,
                file_list = files, 
                max_loop = n_files
            )

            if len(failed) > 0:
                error_msg = "Failed to deploy the following files:\n{}".format(
                    '\n'.join(failed.keys()))
                error_msg = error_msg + '\nSee log for error details.'
                for fail_object, fail_messages in failed.items():
                    logger.debug(f'----- Error for object {fail_object} -----')
                    logger.debug(''.join(fail_messages))
                raise RuntimeError(error_msg)
        else:
            output = execute_files_in_transaction(
                connectable, 
                files, 
                scripting_variables = scripting_variables, 
                include_headers=True,
                commit_transaction = commit_transaction
            )
            if display_output:
                for result in output:
                    logger.info(format_to_table(result))
            
        return True


@rearrange_params({"engine": "connectable"})
def drop_sqlfile_objects(connectable: Union[Engine, Connection], object_type: str, data_src: Union[str, list], message: str):
    """Drop all the objects created in SQL script files of an directory.

    The naming of the files should be consistent!

    Parameters
    ----------
    connectable
        SQL Alchemy engine or connection.
    object_type
        Type of database object.
    data_src
        If data_src is string: path of directory holding the SQL script files.
        If data_src is list: list of filepaths referencing to the SQL script locations.
    message
        Message passed to OperationManager.

    Raises
    ------
    RuntimeError
        If any of the files in given directory/filelist fail to drop after multiple tries.
    """
    with OperationManager(message):
   
        error_msg = None
        connectable_type = type(connectable)
        check_connectable_type(connectable, "drop_sqlfile_objects")

        files = sql_files_found(data_src)
        n_files = len(files)
        if n_files == 0: return False

        if connectable_type == Engine:
            failed = sql_file_loop(
                drop_sql_from_file, 
                connectable,
                object_type, 
                file_list = files, 
                max_loop = n_files
            )
            if len(failed) > 0:
                error_msg = "Failed to drop the following files:\n{}".format('\n'.join(failed.keys()))
                for fail_messages in failed.values():
                    error_msg = error_msg + ''.join(fail_messages)
        else:
            try:
                drop_queries = {}
                for file in files:
                    drop_queries[file] = drop_sql_query(file, object_type)
                drop_files_in_transaction(connectable, drop_queries)
            except:
                error_msg = "Error occured while dropping files."
                error_msg = error_msg + " \n " + format_exc()

        if error_msg is not None:
            raise RuntimeError(error_msg)


@rearrange_params({"engine": "connectable"})
def deploy_sql_from_file(file: str, connectable: Union[Engine, Connection, Session], display_output: bool, scripting_variables: dict, 
        file_transaction: bool = False, commit_transaction: bool = True):
    '''Run single SQL script file.

    Print output as formatted table.

    Parameters
    ----------
    file
        SQL script file path passed to SQLCMD.
    connectable
        SQL Alchemy Engine, Connection or Session.
    display_output
        Indicator to print script output.
    scripting_variables
        Variables passed to SQL script.
    file_transaction
        Indicator to run script in transaction.
    '''
    output = execute_from_file(
        connectable,
        file_path=file,
        scripting_variables=scripting_variables,
        include_headers=True,
        file_transaction=file_transaction,
        commit_transaction=commit_transaction
    )
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
    execute_try_catch(engine, query = drop_sql_query(file, object_type))


def drop_sql_query(file, object_type):
    parts = path.basename(file).split('.')
    # SQL files are assumed to be named in format: schema.object.sql
    # The only exception is assemblies. Assemblies don't have schema.
    if object_type == 'ASSEMBLY':
        object_name = parts[0]
    else:
        if len(parts) != 3:
            raise RuntimeError(f'File {file} not in <schema.object.sql> format.')
        object_name = parts[0] + '.' + parts[1]
    return f"DROP {object_type} {object_name}"


def sql_file_loop(command: Callable[..., Any], *args: Any, file_list: list, max_loop: int = 10) -> dict:
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
            except:
                error_str = '\n------\n' + format_exc()
                errors[file].add(error_str)
        copy_list_loop = copy_list.copy()
    if len(copy_list) > 0:
        return {f: list(errors[f]) for f in copy_list}
    return {}


def check_connectable_type(connectable, func_name):
    connectable_type = type(connectable)
    if not (connectable_type is Engine or connectable_type is Session or connectable_type is Connection):
        error_msg = f"First parameter of function '{func_name}' should be instance of sqlalchemy Engine or Connection. Check your custom actions!"
        raise ValueError(error_msg)
