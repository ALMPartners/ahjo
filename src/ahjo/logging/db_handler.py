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
    def __init__(self, capacity: int = 100, context: Context = None):
        """ Constructor for DatabaseHandler class.

        Arguments:
        -----------
        capacity (int): 
            The maximum number of log records to store in the buffer before flushing to the database.
        context (Context):
            The context object holding the configuration and connection information.
        """
        super().__init__()
        self.context = context
        self.capacity = capacity
        self.buffer = []
        self.locked = True
        self.db_logger = DatabaseLogger(
            context = context,
            log_table_schema = context.configuration.get("log_table_schema", "dbo"),
            log_table = context.configuration.get("log_table", "ahjo_log")
        )


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

        if self.shouldFlush(record = record):
            self.flush()


    def shouldFlush(self, record: logging.LogRecord = None):
        """ Check if the buffer should be flushed.

        Arguments:
        -----------
        record (LogRecord): 
            The log record to be checked.

        Returns:
        -----------
        bool:
            True if the buffer should be flushed, False otherwise.
        """
        if len(self.buffer) >= self.capacity and not self.locked:
            return True
        if record is not None and hasattr(record, "flush") and record.flush:
            return True
        return False


    def flush(self):
        """ Log all records in the buffer to the database and clear the buffer. """
        try:
            self.db_logger.log(self.buffer)
        except:
            pass
        self.buffer = []


    def set_lock(self, locked: bool):
        """ Set the lock status of the handler. """
        self.locked = locked


def get_db_logger_handler(logger: logging.Logger):
    """ Return database logger handler (if exists).
    
    Returns
    -------
    ahjo.logging.db_handler.DatabaseHandler
        Database logger handler.
    """
    for handler in logger.handlers:
        if handler.name == "handler_database":
            return handler