# Ahjo - Database deployment framework
#
# Copyright 2019 - 2024 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

"""Module for logging, printing and error handling deployment process."""
import os
import ahjo
from datetime import datetime
from logging import getLogger
from traceback import format_exception
from logging.config import fileConfig

logger = getLogger('ahjo')


class OperationManager:
    """Class for handling operation context.
    Prints the message and lines at the end.
    """

    def __init__(self, message: str):
        self.message = message

    def __enter__(self):
        logger.info(format_message(self.message))

    def __exit__(self, exc_type, exc_value, traceback):
        if traceback is not None:
            logger.error(''.join(format_exception(
                exc_type, exc_value, traceback)))
        logger.info('------')


def format_message(mssg: str) -> str:
    '''Add timestamp before the message.'''
    timestamp = datetime.now()
    time_string = timestamp.strftime('%Y-%m-%d %H:%M:%S')
    return '[{}] {}'.format(time_string, mssg)


def load_sqlalchemy_logger():
    fileConfig(os.path.join(os.path.dirname(ahjo.__file__), 'resources/logger_sqlalchemy.ini'), disable_existing_loggers=False)
    getLogger('sqlalchemy.engine')
    getLogger('sqlalchemy.pool')
    getLogger('sqlalchemy.dialects')
    getLogger('sqlalchemy.orm')
