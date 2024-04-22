# Ahjo - Database deployment framework
#
# Copyright 2019 - 2024 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

from ahjo.logging.winEventLogger import winEventHandler
from ahjo.logging.db_handler import DatabaseHandler
from ahjo.logging.db_logger import DatabaseLogger

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

def add_db_handler():
    """ Add database handler to the logger configuration. """
    AHJO_LOG_CONFIG["loggers"]["ahjo"]["handlers"] = ["handler_database", "handler_file", "handler_console"]
    AHJO_LOG_CONFIG["loggers"]["alembic"]["handlers"] = ["handler_database", "handler_alembic_console", "handler_file"]
    AHJO_LOG_CONFIG["handlers"]["handler_database"] = {
        "class": "ahjo.logging.db_handler.DatabaseHandler",
        "level": "DEBUG",
        "formatter": "formatter_console",
    }