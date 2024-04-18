# Ahjo - Database deployment framework
#
# Copyright 2019 - 2024 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

import logging
from ahjo.context import Context
from ahjo.logging.db_logger import DatabaseLogger

class DatabaseHandler(logging.Handler):
    """
        Custom logging handler for logging to a database. 
        The handler stores log records in a buffer and flushes them to the database when 
        the buffer is full or when the log record has the attribute flush set to True.
    """
    def __init__(self, capacity: int = 10000):
        """ Constructor for DatabaseHandler class.

        Arguments:
        -----------
        capacity (int): 
            The maximum number of log records to store in the buffer before flushing to the database.

        """
        super().__init__()
        self.context = None
        self.capacity = capacity
        self.buffer = []
    
    def emit(self, record: logging.LogRecord):
        """ Emit a log record to the database. 

        Arguments:
        -----------
        record (LogRecord): 
            The log record to be emitted.

        """
        if hasattr(record, "context"):
            self.context = record.context

        record.formatted_message = self.format(record)
        self.buffer.append(record)

        if hasattr(record, "flush") and record.flush and hasattr(record, "context"):
            self.flush(context = record.context)

    def flush(self, context: Context = None):
        """ Log all records in the buffer to the database and clear the buffer. 

        Arguments:
        -----------
        context (Context): 
            The context object to use for logging. If None, the context object from the last log record is used.

        """
        if context is not None:
            DatabaseLogger(
                log_records = self.buffer,
                context = context,
                log_table_schema = context.configuration.get("log_table_schema", "dbo"),
                log_table = context.configuration.get("log_table", "ahjo_log")
            ).log()

        self.buffer = []


