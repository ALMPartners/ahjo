# Ahjo - Database deployment framework
#
# Copyright 2019 - 2024 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

from ahjo.context import Context
from ahjo.operations.general.git_version import _get_git_commit_info
from datetime import datetime
from sqlalchemy import Column, MetaData, String, Table, DateTime, func, Integer
from sqlalchemy.exc import NoSuchTableError
from logging import getLogger

try:
    from ahjo.version import version as AHJO_VERSION
except ImportError:
    AHJO_VERSION = "?.?.?"

logger = getLogger('ahjo')

class DatabaseLogger:
    """ Class for logging log records to a database. """

    def __init__(self, log_records: list, context: Context, log_table_schema: str, log_table: str, action: str = None):
        """ Constructor for DatabaseLogger class. 
        
        Arguments:
        -----------
        log_records (list): 
            List of log records to be logged to the database.
        context (Context):
            Context object holding the configuration and connection information.
        log_table_schema (str):
            Schema of the log table.
        log_table (str):
            Name of the log table.
        action (str):
            Name of the action that generated the log records.
        """
        self.log_records = log_records
        self.context = context
        self.log_table_schema = log_table_schema
        self.log_table = log_table
        self.user = context.get_conn_info().get("username")
        self.action = action
        self.commit = self.get_git_commit()

    def log(self):
        """ Insert the log records to the database. """

        # Convert log records to a list of rows to be inserted to the database
        log_rows = self.parse_log_records()
        if len(log_rows) == 0:
            return

        # Get the database engine and log table
        engine = self.context.get_engine()
        log_table = self.log_table
        log_table_schema = self.log_table_schema
        metadata = MetaData()

        # Get the log table from the database or create it if it does not exist
        try:
            db_log_table = Table(log_table, metadata, autoload_with=engine, schema=log_table_schema)
        except NoSuchTableError as error:
            logger.info(
                f"Table {log_table_schema + '.' + log_table} not found. Creating the table.")
            db_log_table = Table(
                log_table, metadata,
                Column("id", Integer, primary_key=True),
                Column("timestamp", DateTime, server_default=func.now(), onupdate=func.now()),
                Column("module", String),
                #Column("action", String(100)),
                Column("level", String(20)),
                Column("message", String),
                Column("exc_info", String),
                Column("user", String(100)),
                Column("ahjo_version", String(100)),
                Column("git_version", String(100)),
                Column("git_repository", String),
                schema = log_table_schema
            )
            try:
                metadata.create_all(engine)
            except Exception as error:
                raise Exception(
                    "Log table creation failed. See log for detailed error message."
                ) from error
        
        # Insert log records to the database
        with engine.connect() as connection:
            for log_row in log_rows:
                connection.execute(db_log_table.insert(), log_row)
            connection.commit()
        

    def parse_log_records(self):
        """ Parse log records to a list of dictionaries. 
        
        Returns:
        -----------
        list:
            List of dictionaries containing log record information.
        """
        log_rows = []
        for log_record in self.log_records:
            log_rows.append({
                "timestamp": datetime.fromtimestamp(log_record.created),
                "module": log_record.module,
                #"action": log_record.action if hasattr(log_record, "action") else None,
                "level": log_record.levelname,
                "message": log_record.formatted_message,
                "exc_info": log_record.exc_info,
                #"user": self.user,
                "ahjo_version": AHJO_VERSION,
                "git_version": self.commit,
                "git_repository": self.context.configuration.get("url_of_remote_git_repository", None)
            })
        return log_rows


    def get_git_commit(self):
        """ Get the git commit hash of the current commit.

        Returns:
        -----------
        str or None:
            Git commit hash of the current commit.
        """
        try:
            _, commit = _get_git_commit_info()
            return commit
        except Exception as error:
            logger.debug(f"Failed to get git version. Error: {error}")