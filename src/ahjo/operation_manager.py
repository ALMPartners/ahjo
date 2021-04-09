# Ahjo - Database deployment framework
#
# Copyright 2019, 2020, 2021 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

"""Module for logging, printing and error handling deployment process."""
from datetime import datetime
from logging import getLogger
from traceback import format_exception

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
