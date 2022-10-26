# Ahjo - Database deployment framework
#
# Copyright 2019 - 2022 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

"""
    Operations for SET statements.
"""

from ahjo.operation_manager import OperationManager
from ahjo.database_utilities import execute_query
from sqlalchemy.engine import Engine

def set_xact_abort_and_nocount(engine: Engine, set_value: str = "ON"):
    with OperationManager('Setting XACT_ABORT and NOCOUNT ' + set_value):
        execute_query(engine, "SET XACT_ABORT " + set_value)
        execute_query(engine, "SET NOCOUNT " + set_value)