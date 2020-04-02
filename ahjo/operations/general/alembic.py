# Ahjo - Database deployment framework
#
# Copyright 2019, 2020 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

"""Module for Alembic related operations"""
from os import path
from argparse import Namespace
from logging import getLogger

from alembic import command
from alembic.config import Config

from ahjo.context import AHJO_PATH
from ahjo.database_utilities import execute_query
from ahjo.operation_manager import OperationManager

logger = getLogger('ahjo')


def alembic_config(config_filename):
    """Return altered Alembic config.

    First, read project's alembic configuration (alembic.ini).
    Second, alter project's existing config by passing Ahjo's credential
    configuration file as an 'x' argument and setting 'config_file_name'
    to point to Ahjo's logging configuration file.

    This way Alembic will use Ahjo's loggers and project's configurations
    when running Alembic operations.
    """
    alembic_config = Config('alembic.ini')
    main_section = alembic_config.config_ini_section
    alembic_config.get_section(main_section)    # main section options are set when main section is read
    alembic_config.cmd_opts = Namespace(x=["main_config=" + config_filename])
    alembic_config.config_file_name = path.join(AHJO_PATH, 'resources/logger.ini')
    return alembic_config


def upgrade_db_to_latest_alembic_version(config_filename):
    """Run Alembic 'upgrade head' in the same python-process
    by calling Alembic's API.
    """
    with OperationManager("Running all upgrade migrations"):
        command.upgrade(alembic_config(config_filename), 'head')


def downgrade_db_to_alembic_base(config_filename):
    """Run Alembic 'downgrade base' in the same python-process
    by calling Alembic's API.
    """
    with OperationManager('Downgrading to base'):
        command.downgrade(alembic_config(config_filename), 'base')


def print_alembic_version(engine, alembic_version_table):
    with OperationManager('Checking Alembic version from database'):
        alembic_version_query = f"SELECT * FROM {alembic_version_table}"
        alembic_version = execute_query(engine=engine, query=alembic_version_query)[0][0]
        logger.info("Alembic version: " + alembic_version)
