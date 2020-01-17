# Ahjo - Database deployment framework
#
# Copyright 2019 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

"""Module for Alembic related operations"""
from logging import getLogger

from ahjo.database_utilities import execute_query
from ahjo.operation_manager import OperationManager

logger = getLogger('ahjo')


def run_alembic(alembic_args, config_filename):
    """Runs alembic in the same python-process by calling alembic's entrypoint in python.
    This way alembic shares already given credentials when importing credential_handler.
    """
    import alembic.config
    alembic_args = ['-x', 'main_config=' + config_filename] + alembic_args
    alembic.config.main(argv=alembic_args)


def upgrade_db_to_latest_alembic_version(config_filename):
    with OperationManager("Running all upgrade migrations"):
        run_alembic(['upgrade', 'head'], config_filename)


def downgrade_db_to_alembic_base(config_filename):
    with OperationManager('Downgrading to base'):
        run_alembic(['downgrade', 'base'], config_filename)


def print_alembic_version(engine, alembic_version_table):
    with OperationManager('Checking alembic version from database'):
        alembic_version_query = f"SELECT * FROM {alembic_version_table}"
        alembic_version = execute_query(engine=engine, query=alembic_version_query)[0][0]
        logger.info("Alembic version: " + alembic_version)