# Ahjo - Database deployment framework
#
# Copyright 2019 - 2023 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

"""Operations for loading and printing database information."""

from logging import getLogger
from ahjo.operation_manager import format_message
from sqlalchemy.sql import text
from sqlalchemy.engine import Engine

logger = getLogger('ahjo')


def print_collation(engine: Engine, db_name: str, config_collation_name: str = "Latin1_General_CS_AS", 
                    config_catalog_collation_type_desc: str="DATABASE_DEFAULT") -> None:
    """Log collation information from the database."""

    logger.info(format_message("Loading database connection settings"))

    # Check if the database exists
    if not check_if_db_exists(engine, db_name):
        logger.info(format_message("Skipping database collation check. Database does not exist."))
        return

    try:
        collation, catalog_collation_type_desc, server_edition = get_collation(engine, db_name)
        logger.info("")
        logger.info("   Server edition: " + server_edition)
    except Exception:
        logger.info("Error: Could not get collation information from the database. Check that the database exists and the user has permissions to access it.")
        return

    if config_collation_name != collation:
        logger.warning(
            f"Warning: Ahjo is configured to use {config_collation_name} collation, but the database collation is {collation}"
        )
    else:
        logger.info("   Database collation: " + collation)
        
    if server_edition == "SQL Azure":
        if catalog_collation_type_desc != config_catalog_collation_type_desc:
            logger.error(
                f"Warning: Ahjo is configured to use {config_catalog_collation_type_desc} catalog collation setting, but the database setting is {catalog_collation_type_desc}"
            )
        else:
            if catalog_collation_type_desc is not None: 
                logger.info("   Database catalog collation setting: " + catalog_collation_type_desc)
    
    logger.info("")


def check_if_db_exists(engine: Engine, db_name: str) -> bool:
    """Check if the database exists."""
    try:
        with engine.connect() as connection:
            db_exists = connection.execute(
                text("SELECT COUNT(*) FROM sys.databases WHERE name = :db_name"),
                {"db_name": db_name}
            ).fetchone()[0]
    except Exception:
        db_exists = False

    return db_exists


def get_collation(engine: Engine, db_name: str) -> tuple:
    """Get collation information from the database."""

    collation = None
    catalog_collation_type_desc = None
    server_edition = None

    try:
        with engine.connect() as connection:
            server_edition = connection.execute(
                text("SELECT CAST(SERVERPROPERTY ('Edition') AS NVARCHAR(128))")
            ).fetchone()[0]
            if server_edition == "SQL Azure":
                collation_info = connection.execute(
                    text("SELECT collation_name, catalog_collation_type_desc FROM sys.databases WHERE name = :db_name"),
                    {"db_name": db_name}
                ).fetchone()
                collation = collation_info[0]
                catalog_collation_type_desc = collation_info[1]
            else:
                collation = connection.execute(
                    text("SELECT collation_name FROM sys.databases WHERE name = :db_name"),
                    {"db_name": db_name}
                ).fetchone()[0]
        engine.dispose()
    except Exception as err:
        raise err

    return collation, catalog_collation_type_desc, server_edition