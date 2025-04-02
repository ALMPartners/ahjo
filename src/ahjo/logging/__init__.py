# Ahjo - Database deployment framework
#
# Copyright 2019 - 2026 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

import os
import sys
import ahjo
from logging.config import fileConfig, dictConfig
from logging import getLogger
from ahjo.context import Context
from ahjo.logging.db_logger import load_log_table
from ahjo.database_utilities.sqla_utilities import database_exists
from ahjo.logging.console_formatter import ConsoleFormatterFactory


AHJO_LOG_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "loggers": {
        "root": {"level": "WARN", "handlers": ["handler_console"]},
        "ahjo": {
            "level": "DEBUG",
            "handlers": ["handler_file", "handler_console"],
            "propagate": False,
        },
        "alembic": {
            "level": "INFO",
            "handlers": ["handler_alembic_console", "handler_file"],
            "propagate": False,
        },
    },
    "handlers": {
        "handler_console": {
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
            "level": "INFO",
            "formatter": "formatter_console",
        },
        "handler_alembic_console": {
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
            "level": "INFO",
            "formatter": "formatter_alembic_console",
        },
        "handler_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "ahjo.log",
            "mode": "a+",
            "maxBytes": 1000000,
            "backupCount": 1,
            "level": "DEBUG",
            "formatter": "formatter_file",
        },
    },
    "formatters": {
        "formatter_console": {
            "()": ConsoleFormatterFactory.get_colored_formatter,
            "format": "%(message)s",
        },
        "formatter_alembic_console": {
            "()": ConsoleFormatterFactory.get_colored_formatter,
            "format": "%(levelname).7s [%(name)s] %(message)s",
            "datefmt": "%H:%M:%S",
        },
        "formatter_file": {
            "format": "[%(asctime)s] [%(name)s] %(levelname).7s %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "formatter_db": {
            "()": "ahjo.logging.db_formatter.DatabaseFormatter",
        },
    },
}


def set_console_color_formatting(enable_color: bool = True):
    """Configure the console formatters based on ANSI color support.

    When the console supports ANSI colors, the custom colored formatter factory
    is used. Otherwise the console formatters fall back to the standard
    ``logging.Formatter``.

    Parameters:
    -----------
    enable_color: bool
        Whether colored console output is enabled in the configuration.
    """
    formatters = AHJO_LOG_CONFIG["formatters"]
    for formatter_name in ("formatter_console", "formatter_alembic_console"):
        formatter = formatters[formatter_name]
        if enable_color:
            formatter["()"] = ConsoleFormatterFactory.get_colored_formatter
        else:
            formatter.pop("()", None)


def setup_ahjo_logger(
    enable_database_log: bool = True,
    enable_windows_event_log: bool = False,
    enable_sqlalchemy_log: bool = False,
    context=None,
    test_db_connection=True,
):
    """Set up the logger configuration for ahjo.

    Parameters:
    -----------
    enable_database_log: bool
        Enable database logging.
    enable_windows_event_log: bool
        Enable Windows event logging.
    enable_sqlalchemy_log: bool
        Enable SQLAlchemy logging.

    Returns:
    -----------
    logging.Logger:
        Logger object for ahjo.
    """
    try:
        enable_color = True
        if context is not None:
            enable_color = context.configuration.get("color_console_logging", True)
        set_console_color_formatting(enable_color)

        # Load root logger configuration
        fileConfig(
            os.path.join(os.path.dirname(ahjo.__file__), "resources/logger_root.ini")
        )

        # Setup optional loggers
        if enable_database_log:
            setup_db_logger(context, test_db_connection=test_db_connection)

        if enable_windows_event_log:
            setup_win_event_handler()

        if enable_sqlalchemy_log:
            setup_sqlalchemy_logger()

        # Load ahjo logger
        dictConfig(AHJO_LOG_CONFIG)

        return getLogger("ahjo")

    except Exception as error:
        raise error


def setup_db_logger(context: Context, test_db_connection=True):
    """Setup database logger.

    Parameters:
    -----------
    context: Context
        The context object holding the configuration and connection information.
    test_db_connection: bool
        Test the database connection before setting up the logger.

    Returns:
    -----------
    logging.Logger:
        Logger object for ahjo.
    """
    # Assume that the database exists if we are not testing the connection
    db_exists = database_exists(context.get_engine()) if test_db_connection else True

    if db_exists:

        add_db_handler(
            context=context,
            log_table=load_log_table(
                context,
                context.configuration.get("log_table_schema", "dbo"),
                context.configuration.get("log_table", "ahjo_log"),
            ),
        )

        dictConfig(AHJO_LOG_CONFIG)

        return getLogger("ahjo")


def setup_sqlalchemy_logger():
    """Load the logger configuration for SQLAlchemy."""
    fileConfig(
        os.path.join(os.path.dirname(ahjo.__file__), "resources/logger_sqlalchemy.ini"),
        disable_existing_loggers=False,
    )
    getLogger("sqlalchemy.engine")
    getLogger("sqlalchemy.pool")
    getLogger("sqlalchemy.dialects")
    getLogger("sqlalchemy.orm")


def add_db_handler(context: Context, log_table):
    """Add database handler to the logger configuration.

    Parameters:
    -----------
    context: Context
        The context object holding the configuration and connection information.
    log_table: sqlalchemy.Table
        The log table to which the log records are stored.
    """
    AHJO_LOG_CONFIG["loggers"]["ahjo"]["handlers"].append("handler_database")
    AHJO_LOG_CONFIG["loggers"]["alembic"]["handlers"].append("handler_database")
    AHJO_LOG_CONFIG["handlers"]["handler_database"] = {
        "class": "ahjo.logging.db_handler.DatabaseHandler",
        "level": "DEBUG",
        "formatter": "formatter_db",
        "context": context,
        "log_table": log_table,
    }


def setup_win_event_handler():
    """Add Windows event handler to the logger configuration."""
    AHJO_LOG_CONFIG["loggers"]["ahjo"]["handlers"].append("handler_win_event")
    AHJO_LOG_CONFIG["handlers"]["handler_win_event"] = {
        "class": "ahjo.logging.win_event_logger.winEventHandler",
        "level": "INFO",
        "formatter": "formatter_console",
    }
