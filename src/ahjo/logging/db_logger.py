# Ahjo - Database deployment framework
#
# Copyright 2019 - 2026 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

from ahjo.context import Context
from datetime import datetime
from sqlalchemy import Column, MetaData, String, Table, DateTime, func, Integer
from sqlalchemy.exc import NoSuchTableError
from sqlalchemy import insert

try:
    from ahjo.version import version as AHJO_VERSION
except ImportError:
    AHJO_VERSION = "?.?.?"


class DatabaseLogger:
    """Class for logging log records to a database."""

    def __init__(self, context: Context, log_table: Table, commit: str = None):
        """Constructor for DatabaseLogger class.

        Arguments:
        -----------
        context (Context):
            Context object holding the configuration and connection information.
        log_table (sqlalchemy.Table):
            The log table to which the log records are stored.
        """
        self.context = context
        self.log_table = log_table
        self.user = context.get_conn_info().get("username", None)
        self.commit = commit

    def log(self, log_records: list):
        """Insert the log records to the database."""

        # Convert log records to a list of rows to be inserted to the database
        log_rows = self.parse_log_records(log_records)
        if len(log_rows) == 0:
            return

        # Insert log records to the database
        engine = self.context.get_logger_engine()
        with engine.connect() as conn:
            conn.execute(insert(self.log_table), log_rows)

    def parse_log_records(self, log_records):
        """Parse log records to a list of dictionaries.

        Returns:
        -----------
        list:
            List of dictionaries containing log record information.
        """
        log_rows = []
        for log_record in log_records:
            log_rows.append(
                {
                    "timestamp": datetime.fromtimestamp(log_record.created),
                    "module": log_record.module,
                    "level": log_record.levelname,
                    "message": log_record.formatted_message,
                    "user": self.user,
                    "ahjo_version": AHJO_VERSION,
                    "git_version": self.commit,
                    "git_repository": self.context.configuration.get(
                        "url_of_remote_git_repository", None
                    ),
                }
            )
        return log_rows

    def set_git_commit(self, commit: str):
        """Set the git commit info."""
        self.commit = commit


def load_log_table(context, log_table_schema: str, log_table: str):
    """Load the log table from the database. If the table does not exist, create it.

    Arguments:
    -----------
    context (Context):
        The context object holding the configuration and connection information.
    log_table_schema (str):
        The schema of the log table.
    log_table (str):
        The name of the log table.

    Returns:
    -----------
    sqlalchemy.Table:
        The log table.
    """
    metadata = MetaData()
    try:
        db_log_table = Table(
            log_table,
            metadata,
            autoload_with=context.get_engine(),
            schema=log_table_schema,
        )
    except NoSuchTableError:
        db_log_table = create_log_table(context, log_table_schema, log_table)
    except Exception as error:
        raise error

    return db_log_table


def create_log_table(context, log_table_schema: str, log_table: str):
    """Create the log table in the database.

    Arguments:
    -----------
    context (Context):
        The context object holding the configuration and connection information.
    log_table_schema (str):
        The schema of the log table.
    log_table (str):
        The name of the log table.

    Returns:
    -----------
    sqlalchemy.Table:
        The log table.
    """
    try:
        metadata = MetaData()
        connectable = context.get_engine()
        db_log_table = Table(
            log_table,
            metadata,
            Column("id", Integer, primary_key=True),
            Column(
                "timestamp", DateTime, server_default=func.now(), onupdate=func.now()
            ),
            Column("module", String),
            Column("level", String(20)),
            Column("message", String),
            Column("user", String(100)),
            Column("ahjo_version", String(100)),
            Column("git_version", String(100)),
            Column("git_repository", String),
            schema=log_table_schema,
        )
        metadata.create_all(connectable)
    except Exception as error:
        raise error
    return db_log_table
