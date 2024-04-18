# Ahjo - Database deployment framework
#
# Copyright 2019 - 2024 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

"""Module for Alembic related operations"""
from argparse import Namespace
from logging import getLogger
from os import path

from ahjo.context import AHJO_PATH
from ahjo.interface_methods import rearrange_params
from ahjo.database_utilities import execute_query
from ahjo.operation_manager import OperationManager
from sqlalchemy.engine import Engine
from sqlalchemy.engine import Connection
from typing import Union

from alembic import command
from alembic.config import Config

logger = getLogger('ahjo')


def alembic_config(config_filename: str, connection: Connection = None) -> Config:
    """Return altered Alembic config.

    First, read project's alembic configuration (alembic.ini).
    Second, alter project's existing config by passing Ahjo's credential
    configuration file as an 'x' argument and setting 'config_file_name'
    to point to Ahjo's logging configuration file.

    This way Alembic will use Ahjo's loggers and project's configurations
    when running Alembic operations.
    """
    config = Config('alembic.ini')
    main_section = config.config_ini_section
    # main section options are set when main section is read
    config.get_section(main_section)
    config.cmd_opts = Namespace(x=["main_config=" + config_filename])
    if connection:
        config.attributes["connection"] = connection
    config.config_file_name = path.join(
        AHJO_PATH, 'resources/logger_alembic.ini')
    return config


def upgrade_db_to_latest_alembic_version(config_filename: str, connection: Connection = None):
    """Run Alembic 'upgrade head' in the same python-process
    by calling Alembic's API.
    """
    with OperationManager("Running all upgrade migrations"):
        command.upgrade(alembic_config(config_filename, connection = connection), 'head')


def downgrade_db_to_alembic_base(config_filename: str, connection: Connection = None):
    """Run Alembic 'downgrade base' in the same python-process
    by calling Alembic's API.
    """
    with OperationManager('Downgrading to base'):
        command.downgrade(alembic_config(config_filename, connection = connection), 'base')


@rearrange_params({"engine": "connectable"})
def print_alembic_version(connectable: Union[Engine, Connection], alembic_version_table: str):
    """Print last deployed revision number from Alembic version table."""
    with OperationManager('Checking Alembic version from database'):
        alembic_version_query = f"SELECT * FROM {alembic_version_table}"
        try:
            alembic_version = execute_query(connectable, query=alembic_version_query)[0][0]
            logger.info("Alembic version: " + alembic_version)
        except IndexError:
            logger.info(
                f"Table {alembic_version_table} is empty. No deployed revisions.")
