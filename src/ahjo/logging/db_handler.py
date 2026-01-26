# Ahjo - Database deployment framework
#
# Copyright 2019 - 2025 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

import logging
from ahjo.context import Context
from subprocess import check_output
from ahjo.logging.db_logger import DatabaseLogger
from sqlalchemy import Table


class DatabaseHandler(logging.Handler):
    """
    Custom logging handler for logging to a database.
    The handler stores log records in a buffer and flushes them to the database when
    the buffer is full or when the log record has the attribute flush set to True.
    """

    def __init__(self, context: Context, log_table: Table, capacity: int = 100):
        """Constructor for DatabaseHandler class.

        Arguments:
        -----------
        context (Context):
            The context object holding the configuration and connection information.
        log_table (sqlalchemy.Table):
            The log table to which the log records are stored.
        capacity (int):
            The maximum number of log records to store in the buffer before flushing to the database.
        """
        super().__init__()
        self.context = context
        self.capacity = capacity
        self.buffer = []
        self.db_logger = DatabaseLogger(
            context=context, log_table=log_table, commit=self.get_git_commit()
        )

    def emit(self, record: logging.LogRecord):
        """Emit a log record to the database.

        Arguments:
        -----------
        record (LogRecord):
            The log record to be emitted.

        """
        if hasattr(record, "context"):
            self.context = record.context

        if self.shouldFilter(record):
            return

        record.formatted_message = self.format(record)
        self.buffer.append(record)

        if self.shouldFlush(record=record):
            self.flush()

    def shouldFilter(self, record: logging.LogRecord):
        """Check if the log record should not be logged to the database.

        Arguments:
        -----------
        record (LogRecord):
            The log record to be checked.

        Returns:
        -----------
        bool:
            True if the log record should be filtered, False otherwise.
        """

        if hasattr(record, "module"):
            if record.module == "db_info":
                return True
            if record.module == "interface_methods":
                return True

        if hasattr(record, "record_class"):
            if record.record_class == "line":
                return True
            if record.record_class == "skip_db_record":
                return True

        return False

    def shouldFlush(self, record: logging.LogRecord = None):
        """Check if the buffer should be flushed.

        Arguments:
        -----------
        record (LogRecord):
            The log record to be checked.

        Returns:
        -----------
        bool:
            True if the buffer should be flushed, False otherwise.
        """
        if len(self.buffer) >= self.capacity:
            return True
        if record is not None and hasattr(record, "flush") and record.flush:
            return True
        return False

    def flush(self):
        """Log all records in the buffer to the database and clear the buffer."""
        try:
            self.db_logger.log(self.buffer)
        except:
            pass
        self.buffer = []

    def get_git_commit(self):
        """Get the git commit info.

        Returns:
        -----------
        str or None:
            Git commit hash of the current commit.
        """
        try:
            return (
                check_output(["git", "describe", "--always", "--tags"])
                .decode("utf-8")
                .strip()
            )
        except Exception as error:
            print(f"Failed to get git version. Error: {error}")
        return None
