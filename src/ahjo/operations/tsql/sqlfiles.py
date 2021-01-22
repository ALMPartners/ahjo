# Ahjo - Database deployment framework
#
# Copyright 2019, 2020, 2021 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

"""Module for SQL script file deploy and drop."""
from logging import getLogger
from pathlib import Path
from os import listdir, path

from ahjo.database_utilities import sql_file_loop, drop_tsql_from_file, deploy_tsql_from_file
from ahjo.operation_manager import OperationManager

logger = getLogger('ahjo')


def deploy_sqlfiles(conn_info, directory, message, display_output=False, variable=None):
    """Run every SQL script file found in given directory and print the executed file names.
    If any file in directory cannot be deployed after multiple tries, raise an exeption and
    list failed files to user.

    Parameters
    ----------
    conn_info : dict
        Dictionary holding information needed to establish database connection.
    directory : str
        Path of directory holding the SQL script files.
    message : str
        Message passed to OperationManager.
    display_output : bool
        Indicator to print script output.
    variable : str
        Variable passed to SQL script.

    Raises
    ------
    RuntimeError
        If any of the files in given directory fail to deploy after multiple tries.
    """
    with OperationManager(message):
        if not Path(directory).is_dir():
            logger.warning("Directory not found: " + directory)
            return False
        files = [path.join(directory, f) for f in listdir(directory) if f.endswith('.sql')]
        failed = sql_file_loop(deploy_tsql_from_file, conn_info, display_output, variable, file_list=files, max_loop=len(files))
        if len(failed) > 0:
            error_msg = "Failed to deploy the following files:\n{}".format('\n'.join(failed.keys()))
            for fail_messages in failed.values():
                error_msg = error_msg + ''.join(fail_messages)
            raise RuntimeError(error_msg)
        return True


def drop_sqlfile_objects(engine, object_type, directory, message):
    """Drop all the objects created in SQL script files of an directory.
    The naming of the files should be consistent!

    Parameters
    ----------
    engine : sqlalchemy.engine.Engine
        SQL Alchemy engine.
    object_type : str
        Type of database object.
    directory : str
        Path of directory holding the SQL script files.
    message : str
        Message passed to OperationManager.

    Raises
    ------
    RuntimeError
        If any of the files in given directory fail to drop after multiple tries.
    """
    with OperationManager(message):
        if not Path(directory).is_dir():
            logger.warning("Directory not found: "+ directory)
            return
        files = [path.join(directory, f) for f in listdir(directory) if f.endswith('.sql')]
        failed = sql_file_loop(drop_tsql_from_file, engine, object_type, file_list=files, max_loop=len(files))
        if len(failed) > 0:
            error_msg = "Failed to drop the following files:\n{}".format('\n'.join(failed.keys()))
            for fail_messages in failed.values():
                error_msg = error_msg + ''.join(fail_messages)
            raise RuntimeError(error_msg)
