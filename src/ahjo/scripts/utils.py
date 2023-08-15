# Ahjo - Database deployment framework
#
# Copyright 2019 - 2023 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

'''
    Utility functions for Ahjo scripts.
'''

import os
from logging import getLogger
from ahjo.operations.tsql.collation import get_collation_info
from ahjo.operation_manager import format_message
from sqlalchemy.engine import Engine
from ahjo.interface_methods import load_json_conf

logger = getLogger('ahjo')


def get_config_path(config_filename: str) -> str:
    '''Get configuration filename from environment variable if not given as argument.'''
    if config_filename is None and 'AHJO_CONFIG_PATH' in os.environ:
        return os.environ.get('AHJO_CONFIG_PATH')
    return config_filename


def display_collation_info(engine: Engine, db_name: str, sql_dialect: str = "mssql+pyodbc", 
        config_collation_name: str = "Latin1_General_CS_AS", config_catalog_collation_type_desc: str = "DATABASE_DEFAULT"):
    """Log collation information from the database."""

    if sql_dialect == "mssql+pyodbc":

        logger.info(format_message("Loading database connection settings"))

        try:
            collation, catalog_collation_type_desc, server_edition = get_collation_info(engine, db_name)
        except Exception as e:
            logger.info("Error: Could not get collation information from the database. Check that the database exists and the user has permissions to access it.")
            return
        
        logger.info("Server edition: " + server_edition)

        if config_collation_name != collation:
            logger.warning(
                f"Warning: Ahjo is configured to use {config_collation_name} collation, but the database collation is {collation}"
            )
        else:
            logger.info("Database collation: " + collation)
        
        if server_edition == "SQL Azure":
            if catalog_collation_type_desc != config_catalog_collation_type_desc:
                logger.error(
                    f"Warning: Ahjo is configured to use {config_catalog_collation_type_desc} catalog collation setting, but the database setting is {catalog_collation_type_desc}"
                )
            else:
                if catalog_collation_type_desc is not None: 
                    logger.info("Database catalog collation setting: " + catalog_collation_type_desc)


def config_is_valid(config_path: str, non_interactive: bool = False) -> bool:
    '''Validate configuration file.'''

    # Check if configuration file exists.
    if config_path is None:
        logger.error("Error: Configuration filename is required.")
        return False
    
    configuration = load_json_conf(config_path)

    # Allow only non-interactive authentication methods in non-interactive mode.
    if non_interactive:
        azure_auth = configuration.get("azure_authentication")
        if azure_auth is not None:
            if azure_auth == "ActiveDirectoryInteractive" :
                logger.error("Error: Azure authentication method ActiveDirectoryInteractive is not supported in non-interactive mode.")
                return False
        else:
            if configuration.get("username_file") is None:
                logger.error("Error: Username file is required in non-interactive mode.")
                return False
            if configuration.get("password_file") is None:
                logger.error("Error: Password file is required in non-interactive mode.")
                return False

    return True
