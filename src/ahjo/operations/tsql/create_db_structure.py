# Ahjo - Database deployment framework
#
# Copyright 2019 - 2024 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

"""Operation for settin up database objects from sql files.

Legacy, not recommended approach for db structure creation.
"""

from ahjo.database_utilities import invoke_sqlcmd
from ahjo.operation_manager import OperationManager


def create_db_structure(conn_info: dict):
    """Create DB structure, that is schemas, tables and constraints.
    """
    with OperationManager('Creating structure'):
        invoke_sqlcmd(conn_info, infile='database/create_db_structure.sql')
