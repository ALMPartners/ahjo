# Ahjo - Database deployment framework
#
# Copyright 2019 - 2024 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

from ahjo.context import Context
from ahjo.operations.general.git_version import _get_git_commit_info
from datetime import datetime
from sqlalchemy import Column, MetaData, String, Table, DateTime, func, Integer
from sqlalchemy.exc import NoSuchTableError
from sqlalchemy import insert
from sqlalchemy.orm import Session
from sqlalchemy.engine import Engine
from logging import getLogger

try:
    from ahjo.version import version as AHJO_VERSION
except ImportError:
    AHJO_VERSION = "?.?.?"

logger = getLogger('ahjo')

class DatabaseLogger:
    """ Class for logging log records to a database. """

    def __init__(self, context: Context, log_table: Table):
        """ Constructor for DatabaseLogger class. 
        
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
        #self.action = action
        self.commit = self.get_git_commit()


    def log(self, log_records: list):
        """ Insert the log records to the database. """

        # Convert log records to a list of rows to be inserted to the database
        log_rows = self.parse_log_records(log_records)
        if len(log_rows) == 0:
            return

        # Insert log records to the database
        connectable = self.context.get_connectable()
        with Session(connectable) as session:
            session.execute(insert(self.log_table), log_rows)
            if type(connectable) == Engine:
                session.commit()
        

    def parse_log_records(self, log_records):
        """ Parse log records to a list of dictionaries. 
        
        Returns:
        -----------
        list:
            List of dictionaries containing log record information.
        """
        log_rows = []
        for log_record in log_records:
            log_rows.append({
                "timestamp": datetime.fromtimestamp(log_record.created),
                "module": log_record.module,
                #"action": log_record.action if hasattr(log_record, "action") else None,
                "level": log_record.levelname,
                "message": log_record.formatted_message,
                "exc_info": log_record.exc_info,
                "user": self.user,
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


def load_log_table(context, log_table_schema: str, log_table: str):
    """ Load the log table from the database. If the table does not exist, create it.

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
            autoload_with = context.get_engine(), 
            schema = log_table_schema
        )
    except NoSuchTableError:
        db_log_table = create_log_table(
            context, 
            log_table_schema, 
            log_table
        )
    except Exception as error:
        raise error
        
    return db_log_table


def create_log_table(context, log_table_schema: str, log_table: str):
    """ Create the log table in the database.

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
        metadata.create_all(connectable)
    except Exception as error:
        raise error
    return db_log_table