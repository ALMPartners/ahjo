# Ahjo - Database deployment framework
#
# Copyright 2019 - 2024 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

"""Module for SQL script file deploy and drop."""
import re
import networkx as nx

from collections import defaultdict
from logging import getLogger
from os import listdir, path
from pathlib import Path
from traceback import format_exc
from typing import Any, Callable, Union

from ahjo.interface_methods import rearrange_params
from ahjo.database_utilities import execute_from_file, execute_try_catch, execute_files_in_transaction, drop_files_in_transaction, get_dialect_name
from ahjo.interface_methods import format_to_table
from ahjo.operation_manager import OperationManager
from sqlalchemy.engine import Engine, Connection
from sqlalchemy.orm import Session

logger = getLogger('ahjo')

def sql_files_found(data_src: Union[str, list]):
    """ Find all SQL files in given path or file list. 
    If given path is a single file, return a list containing the file.

    Parameters
    ----------
    data_src
        If data_src is string: path of directory holding the SQL script files. Can be also a single file.
        If data_src is list: list of filepaths referencing to the SQL scripts.
    
    Returns
    -------
    files
        List of SQL script file paths.
    """
    files = []
    data_src_len = len(data_src)

    if isinstance(data_src, str) and data_src_len > 0:

        # Check if data_src is a single sql file
        if data_src.endswith('.sql'):
            if not Path(data_src).is_file():
                logger.warning("File not found: " + data_src)
                return files
            return [data_src]

        if not Path(data_src).is_dir():
            logger.warning("Directory not found: " + data_src)
            return files
        
        files = [path.join(data_src, f) for f in listdir(data_src) if f.endswith('.sql')]

    elif isinstance(data_src, list):

        invalid_params = []
        for arg in data_src:
            if arg.endswith('.sql'):
                files.append(arg)
            elif Path(arg).is_dir():
                files.extend([path.join(arg, f) for f in listdir(arg) if f.endswith('.sql')])
            else:
                invalid_params.append(arg)
        if len(invalid_params) == data_src_len:
            logger.warning("SQL file(s) not found from: " + ' '.join(invalid_params))

    else:
        logger.warning("Parameter 'data_src' should be non-empty string or list.")

    return files


@rearrange_params({"engine": "connectable"})
def deploy_sqlfiles(connectable: Union[Engine, Connection], data_src: Union[str, list], message: str, display_output: bool = False, 
        scripting_variables: dict = None, enable_transaction: bool = None, transaction_scope: str = None, commit_transaction: bool = False, 
        sort_files: bool = True):
    """Run every SQL script file found in given directory/filelist and print the executed file names.

    If any file in directory/filelist cannot be deployed after multiple tries, raise an exeption and
    list failed files to user.

    Parameters
    ----------
    connectable
        SQL Alchemy Engine or Connection.
    data_src
        If data_src is string: path of directory holding the SQL script files. Can be also a single file.
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
    sort_files
        Parse SQL files to find dependencies between them and deploy the files in topological order (mssql only).
        Only views and tables are sorted based on dependencies.

    Returns
    -------
    output
        Dictionary with file names as keys and output as values.

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
        dialect_name = get_dialect_name(connectable)
        sort_files = True if sort_files and isinstance(data_src, str) and dialect_name == "mssql" else False
        files = sql_files_found(data_src)
        n_files = len(files)
        error_msg = None
        if n_files == 0: return False
        max_loop = 1 if sort_files else n_files
        
        # Sort views and tables based on dependencies to avoid errors related to missing objects (mssql only)
        if sort_files and re.search(r"views|tables", data_src, re.IGNORECASE):
            try:
                object_type = "view" if re.search(r"views", data_src, re.IGNORECASE) else "table"
                files = topological_sort(files, object_types = [object_type])
            except:
                logger.warning("Failed to sort files based on dependencies.")
                logger.warning("Files are executed in the order they are found.")
                max_loop = n_files

        # Set transaction scope to 'files' if not set by user and connectable is not Engine.
        transaction_scope = "files" if (enable_transaction is None and connectable_type is not Engine) else transaction_scope

        if transaction_scope != "files":
            failed, output = sql_file_loop(
                deploy_sql_from_file, 
                connectable,
                display_output, 
                scripting_variables, 
                True if enable_transaction and transaction_scope == "file" else False,
                True if connectable_type is Engine else commit_transaction,
                file_list = files,
                max_loop = max_loop
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
                for filepath in output.keys():
                    logger.info(format_to_table(output[filepath]))

        return output


def topological_sort(files: list, object_types: list = None) -> list:
    '''Sort files based on their dependencies.

    Parameters
    ----------
    files
        List of file paths.
    object_types
        List of object types to sort based on dependencies.

    Returns
    -------
    sorted_files
        List of file paths sorted based on dependencies.
    '''
    G = create_dependency_graph(files, object_types)
    sorted_files = list(reversed(list(nx.topological_sort(G))))
                
    return sorted_files


def create_dependency_graph(data_src: Union[str, list], object_types: list = None) -> object:
    '''Create dependency graph based on SQL script files.

    Parameters
    ----------
    data_src
        If data_src is string: path of directory holding the SQL script files. Can be also a single file.
        If data_src is list: list of filepaths referencing to the SQL scripts.
    object_types
        List of object types to parse for dependencies. 
        Valid object types: 'table', 'view', 'procedure', 'function', 'trigger', 'index', 'partition'.
        By default all object types are included.

    Returns
    -------
    G
        NetworkX DiGraph object.
    '''
    G = nx.DiGraph()
    files = sql_files_found(data_src)
    objects_to_files = {}
    file_strs = {}
    object_types_whitelist = ["table", "view", "procedure", "function", "trigger", "index", "partition"]

    try:
        # Select only valid object types
        if object_types is not None:
            object_types = [object_type for object_type in object_types if object_type in object_types_whitelist]
            if len(object_types) == 0:
                raise ValueError("Invalid object types. Valid object types: 'table', 'view', 'procedure', 'function', 'trigger', 'index', 'partition'")
        else:
            object_types = object_types_whitelist

        for file_path in files:

            with open(file_path, 'r') as file:
                sql_script_str = file.read()

            sql_script_str = remove_comments_from_sql_string(sql_script_str)
            file_strs[file_path] = sql_script_str
            created_objects = find_created_objects(sql_script_str, object_types)
            n_created_objects = 0
            created_object_type = None

            for object_type, object_names in created_objects.items():
                for object_name in object_names:
                    objects_to_files[object_name] = file_path
                    n_created_objects += 1
                    created_object_type = object_type

            if n_created_objects == 0:
                created_object_type = None
            if n_created_objects > 1:
                created_object_type = "multiple"

            G.add_node(file_path, object_type = "file", objects = created_objects, created_object_type = created_object_type)
        
        for file_path in files:

            file_dependencies = find_dependencies(file_strs[file_path], object_types)
            
            for file_object in file_dependencies:
                if file_object not in objects_to_files:
                    continue
                G.add_edge(file_path, objects_to_files[file_object])

    except Exception as e:
        raise e

    return G


def find_created_objects(sql_script: str, object_types: list) -> dict:
    """Find all created objects in SQL script.
    
    Parameters
    ----------
    sql_script
        SQL script as string.
    object_types
        List of object types to search for.

    Returns
    -------
    created_objects
        Dictionary with object types as keys and object names as values.
    """
    # Regular expressions to match SQL object creation statements
    object_patterns = {
        "table": re.compile(r"\bCREATE\s+TABLE\s+([a-zA-Z0-9_\[\]\.]+)", re.IGNORECASE),
        "view": re.compile(r"\bCREATE\s+VIEW\s+([a-zA-Z0-9_\[\]\.]+)", re.IGNORECASE),
        "procedure": re.compile(r"\bCREATE\s+PROCEDURE\s+([a-zA-Z0-9_\[\]\.]+)", re.IGNORECASE),
        "function": re.compile(r"\bCREATE\s+FUNCTION\s+([a-zA-Z0-9_\[\]\.]+)", re.IGNORECASE),
        "trigger": re.compile(r"\bCREATE\s+TRIGGER\s+([a-zA-Z0-9_\[\]\.]+)", re.IGNORECASE),
        "index": re.compile(r"\bCREATE\s+INDEX\s+([a-zA-Z0-9_\[\]\.]+)", re.IGNORECASE),
        "partition": re.compile(r"\bCREATE\s+PARTITION\s+FUNCTION\s+([a-zA-Z0-9_\[\]\.]+)", re.IGNORECASE)
    }
    created_objects = {}

    # Find all created objects in the SQL script
    for object_type in object_types:
        pattern = object_patterns[object_type]
        matches = pattern.findall(sql_script)
        matches = [match.replace('[', '').replace(']', '') for match in matches]
        created_objects[object_type] = matches

    return created_objects


def find_dependencies(sql_script: str, object_types: list) -> list:
    """ Find all object dependencies in SQL script. 

    Parameters
    ----------
    sql_script
        SQL script as string.
    object_types
        List of object types to search for.

    Returns
    -------
    dependencies
        List of object names.
    """
    dependencies = []
    patterns = {
        "table": re.compile(r'\b(?:FROM|JOIN|INTO|UPDATE|DELETE FROM)\s+(?:\[?([a-zA-Z0-9_]+)\]?\.)?\[?([a-zA-Z0-9_]+)\]?'),
        "procedure": re.compile(r'\bEXEC\s+(?:\[?([a-zA-Z0-9_]+)\]?\.)?\[?([a-zA-Z0-9_]+)\]?'),
        "view": re.compile(r'\b(?:FROM|JOIN|INTO|UPDATE|DELETE FROM)\s+(?:\[?([a-zA-Z0-9_]+)\]?\.)?\[?([a-zA-Z0-9_]+)\]?'),
        "partition": re.compile(r'\bAS\s+PARTITION\s+(?:\[?([a-zA-Z0-9_]+)\]?\.)?\[?([a-zA-Z0-9_]+)\]?')
    }
    
    for pattern in object_types:

        if pattern not in patterns:
            continue

        pattern = patterns[pattern]
        matches = pattern.findall(sql_script)
        for match in matches:

            # If there's a schema, join schema and object name
            if match[0]:
                object_name = f"{match[0]}.{match[1]}"
            else:
                object_name = match[1]

            object_name = object_name.replace('[', '').replace(']', '')
            dependencies.append(object_name)

    return dependencies


def remove_comments_from_sql_string(sql_string: str): 
    '''Remove comments from SQL string.

    Parameters
    ----------
    sql_string
        SQL string.

    Returns
    -------
    sql_string
        SQL string without comments.
    '''
    # Remove comments from SQL string
    sql_string = re.sub(r'/\*.*?\*/', '', sql_string, flags=re.DOTALL)
    sql_string = re.sub(r'--.*', '', sql_string)
    return sql_string


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
        If data_src is string: path of directory holding the SQL script files. Can be also a single file.
        If data_src is list: list of filepaths referencing to the SQL scripts.
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
            failed, _ = sql_file_loop(
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
        file_transaction: bool = False, commit_transaction: bool = True) -> list:
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

    Returns
    -------
    output
        Query output as list. If query returns no output, empty list is returned.

    '''
    output = execute_from_file(
        connectable,
        file_path=file,
        scripting_variables=scripting_variables,
        include_headers=True,
        file_transaction=file_transaction,
        commit_transaction=commit_transaction
    )
    logger.info(path.basename(file), extra={"record_class": "deployment"})
    if display_output:
        logger.info(format_to_table(output))

    return output


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
    errors
        Dictionary with file names as keys and error messages as values.
    outputs
        outputs: Dictionary with file names as keys and output as values.
    '''
    copy_list = file_list.copy()
    copy_list_loop = copy_list.copy()
    errors = defaultdict(set)
    outputs = {}
    for _ in range(max_loop):
        for file in copy_list_loop:
            try:
                output = command(file, *args)
                copy_list.remove(file)
                outputs[file] = output
            except:
                error_str = '\n------\n' + format_exc()
                errors[file].add(error_str)
        copy_list_loop = copy_list.copy()
    if len(copy_list) > 0:
        return {f: list(errors[f]) for f in copy_list}, outputs
    return {}, outputs


def check_connectable_type(connectable, func_name):
    connectable_type = type(connectable)
    if not (connectable_type is Engine or connectable_type is Session or connectable_type is Connection):
        error_msg = f"First parameter of function '{func_name}' should be instance of sqlalchemy Engine or Connection. Check your custom actions!"
        raise ValueError(error_msg)
