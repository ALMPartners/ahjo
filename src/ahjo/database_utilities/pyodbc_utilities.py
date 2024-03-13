# Ahjo - Database deployment framework
#
# Copyright 2019 - 2024 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

"""Utility functions for pyodbc. """

import pyodbc
from sqlalchemy.engine import Engine, Connection
from typing import Union

def execute_queries(connectable: Union[Engine, Connection], queries: list, commit: bool = False):
    """Execute a list of queries with a cursor.

    Arguments
    ---------
    connectable
        SQL Alchemy Engine or Connection.
    queries
        List of tuples. Each tuple contains a query and a list of parameters.
    commit
        If True, commit the transaction.
    
    Returns
    -------
    tuple
        Tuple of two lists: results and errors.
    """
    raw_connection = connectable.raw_connection() if isinstance(connectable, Engine) else connectable.connection
    cursor = raw_connection.cursor()
    results = []
    errors = []

    for i in range(len(queries)):
        batch_results, batch_errors = execute_query(
            cursor, 
            queries[i][0], 
            parameters = queries[i][1]
        )
        if batch_results: results.extend(batch_results)
        if batch_errors: errors.extend(batch_errors)

    if commit: 
        cursor.commit()
        cursor.close()

    return results, errors


def execute_query(cursor: pyodbc.Cursor, query: str, parameters: list = None, commit: bool = False, close: bool = False) -> tuple:
    """Execute a query with a cursor.

    Arguments
    ---------
    cursor
        pyodbc cursor object.
    query
        SQL query to be executed.
    parameters
        List of parameters to be used in the query.
    commit
        If True, commit the transaction.
    close
        If True, close the cursor.

    Returns
    -------
    tuple
        Tuple of two lists: results and errors.
    """
    results = []
    errors = []

    try:
        cursor.execute(query, parameters) if parameters else cursor.execute(query)
    except Exception as e:
        errors.append(e)

    while True:
        try:
            results.append(cursor.fetchall())
            cursor.nextset()
        except:
            if cursor.nextset() is None:
                errors.append(cursor.fetchall())
            break

    if commit: cursor.commit()
    if close: cursor.close()

    return results, errors