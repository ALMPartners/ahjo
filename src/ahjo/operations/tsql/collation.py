# Ahjo - Database deployment framework
#
# Copyright 2019 - 2023 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

""" Module for database collation information."""

from sqlalchemy.sql import text
from sqlalchemy.engine import Engine


def get_collation_info(engine: Engine, db_name: str) -> tuple:
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