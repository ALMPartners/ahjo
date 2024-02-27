# Ahjo - Database deployment framework
#
# Copyright 2019 - 2024 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

"""
    Module for SQL Server script file deploy.
"""

import ahjo.operations as op
from ahjo.operations.tsql.set_statements import xact_abort_and_nocount_decorator as xact_abort_and_nocount

@xact_abort_and_nocount
def deploy_mssql_sqlfiles(engine, data_src, message):
    """Set XACT_ABORT and NOCOUNT ON, deploy sql files and finally set XACT_ABORT and NOCOUNT OFF."""
    op.deploy_sqlfiles(engine, data_src, message)