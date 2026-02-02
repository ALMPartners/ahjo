# Ahjo - Database deployment framework
#
# Copyright 2019 - 2026 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

"""Bulk insert with SQL Alchemy Core."""

from logging import getLogger
from time import time
from typing import Generator, Optional

from sqlalchemy import Table, event
from sqlalchemy.engine import Engine, ExceptionContext, Connection, interfaces

logger = getLogger("ahjo")


def bulk_insert_into_database(
    engine: Engine,
    reflected_table: Table,
    records: list,
    chunk_size: Optional[int] = 1000,
    connection: Optional[Connection] = None,
):
    """Insert multiple rows of data to target table.
    If error occurs, print and log only the original driver
    error (no insert statements).

    Arguments
    ---------
    engine: sqlalchemy.engine.Engine
        SQL Alchemy engine.
    reflected_table : sqlalchemy.schema.Table
        Table, where rows are inserted.
    records : list
        List of dictionaries containing columns and values to insert.
    chunk_size : int
        Defines in how big chunks records are passed to insert.
    """
    table_name_with_schema = (
        reflected_table.schema + "." if reflected_table.schema else ""
    ) + reflected_table.name
    with BulkInsertContext(engine, table_name_with_schema):
        connection_obj = engine.connect() if connection is None else connection
        for r in chunks(records, chunk_size):
            connection_obj.execute(reflected_table.insert(), r)
        if connection is None:
            connection_obj.commit()
            connection_obj.close()


class BulkInsertContext:
    """Before bulk insert, register event listeners.

    - If dialect is pyodbc, enable fast_executemany on 'before_cursor_execute' event.
    - Bind handler_bulk_insert_error to 'handle_error' event.

    After bulk insert, remove event listeners.
    """

    def __init__(self, engine: Engine, table_name: str):
        self.engine = engine
        self.table_name = table_name
        self.enable_fast_executemany = True if engine.driver == "pyodbc" else False
        self.start_time = time()

    def __enter__(self):
        logger.info(f"Executing bulk insert to table {self.table_name}")
        if self.enable_fast_executemany is True:
            self.engine.dialect.use_insertmanyvalues = False
            self.engine.dialect.bind_typing = interfaces.BindTyping.NONE
            logger.debug("Enabling pyodbc fast_executemany")
            event.listen(self.engine, "before_cursor_execute", handler_fast_executemany)
        event.listen(self.engine, "handle_error", handler_bulk_insert_error)

    def __exit__(self, exc_type, exc_value, traceback):
        event.remove(self.engine, "handle_error", handler_bulk_insert_error)
        if self.enable_fast_executemany is True:
            event.remove(self.engine, "before_cursor_execute", handler_fast_executemany)
            self.engine.dialect.use_insertmanyvalues = True
            self.engine.dialect.bind_typing = interfaces.BindTyping.SETINPUTSIZES
        if traceback is None:
            duration = time() - self.start_time
            logger.info(f"{self.table_name} insert took {duration:.2f} seconds")


def handler_fast_executemany(conn, cursor, statement, params, context, executemany):
    """Enable pyodbc fast_executemany.
    Binds to SQL Alchemy Core Event 'before_cursor_execute'.
    """
    cursor.fast_executemany = True


def handler_bulk_insert_error(exception_context: ExceptionContext):
    """Raise originally caught exception if bulk insert fails.
    Binds to SQL Alchemy Core Event 'handle_error'.
    """
    logger.error("Error during bulk insert:")
    raise Exception(exception_context.original_exception)


def chunks(lst: list, n: int) -> Generator[list, None, None]:
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i : i + n]
