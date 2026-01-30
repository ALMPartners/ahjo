# Ahjo - Database deployment framework
#
# Copyright 2019 - 2026 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

"""Utility functions for pyodbc."""

from sqlalchemy.engine import Engine, Connection
from typing import Union


def execute_queries(
    connectable: Union[Engine, Connection], queries: list, commit: bool = True
):
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
    results: list
        List of results for each query that returns results.
    """
    raw_connection = (
        connectable.raw_connection()
        if isinstance(connectable, Engine)
        else connectable.connection
    )
    try:
        cursor = raw_connection.cursor()
        results = []
        for sql, params in queries:
            cursor.execute(sql, params or [])

            while True:
                if cursor.description:
                    results.append(cursor.fetchall())
                if not cursor.nextset():
                    break

            if commit:
                raw_connection.commit()

        cursor.close()

    except Exception:
        raise

    if commit:
        raw_connection.close()

    return results
