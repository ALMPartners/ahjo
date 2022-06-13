# Ahjo - Database deployment framework
#
# Copyright 2019, 2020, 2021 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0


"""Operation for setting up database permissions from a file
"""
from ahjo.database_utilities import invoke_sqlcmd
from ahjo.operation_manager import OperationManager
from ahjo.operations.general.sqlfiles import deploy_sql_from_file
from typing import Union
from sqlalchemy.engine import Engine


def create_db_permissions(connection: Union[dict, Engine], db_permissions: list = [{"source": "database/create_db_permissions.sql"}]):
    """Set permissions for DB Login."""
    with OperationManager('Setting login permissions'):
        for permission in db_permissions:
            src_file = permission.get("source")
            if connection.__class__.__name__ == "Engine":
                deploy_sql_from_file(src_file, connection, False, permission.get("variables"))
            else:
                invoke_sqlcmd(connection, infile = src_file, variable=permission.get("variables"))