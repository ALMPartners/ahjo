# Ahjo - Database deployment framework
#
# Copyright 2019, 2020 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0


"""Operation for settin up database permissions from a file
"""
from ahjo.database_utilities import invoke_sqlcmd
from ahjo.operation_manager import OperationManager

def create_db_permissions(conn_info):
    """Set permissions for DB Login.
    Used mainly in Django projects."""
    with OperationManager('Setting login permissions'):
        invoke_sqlcmd(conn_info, infile='database/create_db_permissions.sql')