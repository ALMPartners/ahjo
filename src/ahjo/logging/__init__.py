# Ahjo - Database deployment framework
#
# Copyright 2019 - 2024 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

import os
import ahjo
from ahjo.logging.win_event_logger import winEventHandler
from ahjo.logging.db_handler import DatabaseHandler
from ahjo.logging.db_logger import DatabaseLogger
from logging.config import fileConfig, dictConfig
from logging import getLogger


AHJO_LOG_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "loggers":{
        "root": {
            "level": "WARN",
            "handlers": ["handler_console"]
        },
        "ahjo":{
            "level": "DEBUG",
            "handlers": ["handler_file", "handler_console"],
            "propagate": False
        },
        "alembic":{
            "level": "INFO",
            "handlers": ["handler_alembic_console", "handler_file"],
            "propagate": False
        },
    },
    "handlers":{ 
        "handler_console":{
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
            "level": "INFO",
            "formatter": "formatter_console"
        },
        "handler_alembic_console":{
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
            "level": "INFO",
            "formatter": "formatter_alembic_console"
        },
        "handler_file":{
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "ahjo.log",
            "mode": "a+",
            "maxBytes": 1000000,
            "backupCount": 1,
            "level": "DEBUG",
            "formatter": "formatter_file"
        }
    },
    "formatters":{
        "formatter_console":{
            "format": "%(message)s"
        },
        "formatter_alembic_console":{
            "format": "%(levelname).7s [%(name)s] %(message)s",
            "datefmt": "%H:%M:%S"
        },
        "formatter_file":{
            "format": "[%(asctime)s] [%(name)s] %(levelname).7s %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S"
        }
    }
}

def setup_ahjo_logger(config: dict):
    """ Set up the logger configuration for ahjo. 
    
    Parameters:
    -----------
    config: dict
        Configuration dictionary containing the parameters for the logger configuration.

    Returns:
    -----------
    logging.Logger:
        Logger object for ahjo.
    """
    # Load root logger configuration
    fileConfig(os.path.join(os.path.dirname(ahjo.__file__), 'resources/logger_root.ini'))

    # Load optional loggers
    if config.get("enable_database_logging", True):
        add_db_handler()
    if config.get("windows_event_log", False):
        add_win_event_handler()
    if config.get("enable_sqlalchemy_logging", False):
        load_sqlalchemy_logger()
    
    # Load ahjo logger
    dictConfig(AHJO_LOG_CONFIG)

    return getLogger('ahjo')


def load_sqlalchemy_logger():
    """ Load the logger configuration for SQLAlchemy. """
    fileConfig(os.path.join(os.path.dirname(ahjo.__file__), 'resources/logger_sqlalchemy.ini'), disable_existing_loggers=False)
    getLogger('sqlalchemy.engine')
    getLogger('sqlalchemy.pool')
    getLogger('sqlalchemy.dialects')
    getLogger('sqlalchemy.orm')


def add_db_handler():
    """ Add database handler to the logger configuration. """
    AHJO_LOG_CONFIG["loggers"]["ahjo"]["handlers"].append("handler_database")
    AHJO_LOG_CONFIG["loggers"]["alembic"]["handlers"].append("handler_database")
    AHJO_LOG_CONFIG["handlers"]["handler_database"] = {
        "class": "ahjo.logging.db_handler.DatabaseHandler",
        "level": "DEBUG",
        "formatter": "formatter_console",
    }

def add_win_event_handler():
    """ Add Windows event handler to the logger configuration. """
    AHJO_LOG_CONFIG["loggers"]["ahjo"]["handlers"].append("handler_win_event")
    AHJO_LOG_CONFIG["handlers"]["handler_win_event"] = {
        "class": "ahjo.logging.win_event_logger.winEventHandler",
        "level": "INFO",
        "formatter": "formatter_console",
    }