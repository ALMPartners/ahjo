# Ahjo - Database deployment framework
#
# Copyright 2019 - 2023 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

"""Module for database information related operations."""

from ahjo.operations.tsql.db_info import print_collation as print_collation_tsql
from ahjo.context import Context


def print_db_collation(context: Context):
    """Log collation information from the database. Currently only supports MSSQL."""
    engine = context.get_engine()
    db_name = context.configuration.get("target_database_name")
    sql_dialect = context.configuration.get("sql_dialect", "mssql+pyodbc")
    config_collation_name = context.configuration.get("database_collation", "Latin1_General_CS_AS")
    config_catalog_collation_type_desc = context.configuration.get("catalog_collation_type_desc", "DATABASE_DEFAULT")

    if sql_dialect == "mssql+pyodbc":
        print_collation_tsql(engine, db_name, config_collation_name, config_catalog_collation_type_desc)


