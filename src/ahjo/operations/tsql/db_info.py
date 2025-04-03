# Ahjo - Database deployment framework
#
# Copyright 2019 - 2024 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

"""Operations for loading and printing database information."""

from logging import getLogger
from ahjo.context import Context
from ahjo.operation_manager import format_message
from sqlalchemy.sql import text
from sqlalchemy.engine import Engine

logger = getLogger("ahjo")


def display_db_info(context: Context) -> None:
    """Log collation information from the database."""

    config_collation_name = context.configuration.get(
        "database_collation", "Latin1_General_CS_AS"
    )
    config_catalog_collation_type_desc = context.configuration.get(
        "catalog_collation_type_desc", "DATABASE_DEFAULT"
    )

    engine = context.get_engine()
    db_name = context.get_conn_info().get("database")
    logger.info(format_message("Loading database connection settings"))

    # Check if the database exists
    if not check_if_db_exists(engine, db_name):
        logger.info(
            format_message(
                "Skipping database connection test. Database does not exist or connection failed."
            )
        )
        return

    try:
        db_info = get_db_info(engine, db_name)
        db_info["Server name"] = context.get_conn_info().get("server")
        server_edition = db_info.get("Server Edition", None)
        collation = db_info.get("Database collation", None)
        catalog_collation_type_desc = db_info.get("Database catalog collation", None)
        label_width = (
            max(
                len(label) + 1 for label in db_info.keys() if db_info[label] is not None
            )
            + 2
        )
        logger.info("")
        bold_ansi = "\033[1m"
        reset_ansi = "\033[0m"
        for key, value in db_info.items():
            label = f"{bold_ansi}{key}:{reset_ansi}"
            if value:
                logger.info(
                    "   "
                    + label.ljust(label_width + len(bold_ansi) + len(reset_ansi))
                    + str(value)
                )

    except Exception:
        logger.info(
            "Error: Could not get collation information from the database. Check that the database exists and the user has permissions to access it."
        )
        return

    if config_collation_name != collation:
        logger.warning(
            f"Warning: Ahjo is configured to use {config_collation_name} collation, but the database collation is {collation}"
        )

    if server_edition == "SQL Azure":
        if catalog_collation_type_desc != config_catalog_collation_type_desc:
            logger.error(
                f"Warning: Ahjo is configured to use {config_catalog_collation_type_desc} catalog collation setting, but the database setting is {catalog_collation_type_desc}"
            )

    logger.info("")


def check_if_db_exists(engine: Engine, db_name: str) -> bool:
    """Check if the database exists."""
    try:
        with engine.connect() as connection:
            db_exists = connection.execute(
                text("SELECT COUNT(*) FROM sys.databases WHERE name = :db_name"),
                {"db_name": db_name},
            ).fetchone()[0]
    except Exception:
        db_exists = False

    return db_exists


def get_db_info(engine: Engine, db_name: str) -> tuple:
    """Get collation information from the database."""

    db_info = {
        "Server name": None,
        "Host name": None,
        "Login name": None,
        "Database": None,
        "Database collation": None,
        "Database catalog collation": None,
        "SQL version": None,
        "Server Edition": None,
    }

    try:
        with engine.connect() as connection:

            conn_info = connection.execute(
                text(
                    """
                    SELECT
                        CAST(SERVERPROPERTY ('Edition') AS NVARCHAR(128)),
                        SUSER_NAME() AS login_name,
                        HOST_NAME() AS host_name,
                        DB_NAME() AS current_database,
                        SERVERPROPERTY('ProductVersion') AS sql_version
                """
                )
            ).fetchone()

            db_info["Server edition"] = conn_info[0]
            db_info["Login name"] = conn_info[1]
            db_info["Host name"] = conn_info[2]
            db_info["Database"] = conn_info[3]
            db_info["SQL version"] = conn_info[4]

            if db_info["Server edition"] == "SQL Azure":
                collation_info = connection.execute(
                    text(
                        "SELECT collation_name, catalog_collation_type_desc FROM sys.databases WHERE name = :db_name"
                    ),
                    {"db_name": db_name},
                ).fetchone()
                db_info["Database collation"] = collation_info[0]
                db_info["Database catalog collation"] = collation_info[1]
            else:
                collation = connection.execute(
                    text(
                        "SELECT collation_name FROM sys.databases WHERE name = :db_name"
                    ),
                    {"db_name": db_name},
                ).fetchone()[0]
                db_info["Database collation"] = collation
        engine.dispose()
    except Exception as err:
        raise err

    return db_info
