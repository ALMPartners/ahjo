# Ahjo - Database deployment framework
#
# Copyright 2019 - 2025 ALM Partners Oy
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

ALEMBIC_API_COMMANDS = {
    "check",
    "upgrade",
    "downgrade",
    "current",
    "history",
    "heads",
    "branches",
    "stamp",
    "revision",
    "edit",
    "ensure_version",
    "init",
    "list_templates",
    "merge",
    "show",
}

logger = getLogger("ahjo")


def alembic_config(config_filename: str, connection: Connection = None) -> Config:
    """Return altered Alembic config.

    First, read project's alembic configuration (alembic.ini).
    Second, alter project's existing config by passing Ahjo's credential
    configuration file as an 'x' argument and setting 'config_file_name'
    to point to Ahjo's logging configuration file.

    This way Alembic will use Ahjo's loggers and project's configurations
    when running Alembic operations.
    """
    config = Config("alembic.ini")
    main_section = config.config_ini_section
    # main section options are set when main section is read
    config.get_section(main_section)
    config.cmd_opts = Namespace(x=["main_config=" + config_filename])
    if connection:
        config.attributes["connection"] = connection
    config.config_file_name = path.join(AHJO_PATH, "resources/logger_alembic.ini")
    return config


def alembic_command(
    config_filename: str,
    command_name: str,
    connection: Connection = None,
    *args,
    **kwargs,
):
    """Wrapper for alembic API commands.

    Arguments
    ---------
    config_filename : str
        Path to the project's configuration file.
    command_name : str
        Alembic API command to run.
        Command names can be found from https://alembic.sqlalchemy.org/en/latest/api/commands.html.
    connection : Connection
        SQL Alchemy Connection object.
    *args, **kwargs
        Arguments to pass to the Alembic command.

    Raises
    ------
    ValueError
        If command_name is not in ALEMBIC_API_COMMANDS.
    """
    if command_name not in ALEMBIC_API_COMMANDS:
        raise ValueError(f"Command {command_name} not in Alembic API commands.")
    with OperationManager(f"Running Alembic command: {command_name}"):
        getattr(command, command_name)(
            config=alembic_config(config_filename, connection=connection),
            *args,
            **kwargs,
        )


def upgrade_db_to_latest_alembic_version(
    config_filename: str, connection: Connection = None
):
    """Run Alembic 'upgrade head' in the same python-process
    by calling Alembic's API.
    """
    with OperationManager("Running all upgrade migrations"):
        command.upgrade(alembic_config(config_filename, connection=connection), "head")


def downgrade_db_to_alembic_base(config_filename: str, connection: Connection = None):
    """Run Alembic 'downgrade base' in the same python-process
    by calling Alembic's API.
    """
    with OperationManager("Downgrading to base"):
        command.downgrade(
            alembic_config(config_filename, connection=connection), "base"
        )


@rearrange_params({"engine": "connectable"})
def print_alembic_version(
    connectable: Union[Engine, Connection], alembic_version_table: str
):
    """Print last deployed revision number from Alembic version table."""
    with OperationManager("Checking Alembic version from database"):
        alembic_version_query = f"SELECT * FROM {alembic_version_table}"
        try:
            alembic_version = execute_query(connectable, query=alembic_version_query)[
                0
            ][0]
            logger.info("Alembic version: " + alembic_version)
        except IndexError:
            logger.info(
                f"Table {alembic_version_table} is empty. No deployed revisions."
            )
