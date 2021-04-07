import logging
from os import chdir, getcwd

import ahjo.operations.tsql.db_object_properties as dop
import pytest

from .utils import run_alembic_action

DESC_QUERY = """
    SELECT CAST(value as VARCHAR(8000))
    FROM sys.extended_properties
    WHERE name = 'Description' AND value != ''"""

FLAG_QUERY = """
    SELECT CAST(value as VARCHAR(8000))
    FROM sys.extended_properties
    WHERE name = 'Flag' AND value != ''"""


@pytest.mark.mssql
class TestWithSQLServer():

    @pytest.fixture(scope='function', autouse=True)
    def db_objects_setup_and_teardown(self, mssql_sample, mssql_engine):
        """Deploy objects without updating object properties and git version."""
        self.engine = mssql_engine
        old_cwd = getcwd()
        chdir(mssql_sample)
        run_alembic_action('upgrade', 'head')
        yield
        run_alembic_action('downgrade', 'base')
        chdir(old_cwd)

    def test_objects_should_not_have_external_properties_before_update(self):
        result = self.engine.execute(DESC_QUERY)
        descriptions = result.fetchall()
        result = self.engine.execute(FLAG_QUERY)
        flags = result.fetchall()
        assert len(descriptions) == 0
        assert len(flags) == 0

    def test_objects_should_have_external_properties_after_update(self):
        dop.update_db_object_properties(self.engine, ['store', 'report'])
        result = self.engine.execute(DESC_QUERY)
        descriptions = result.fetchall()
        result = self.engine.execute(FLAG_QUERY)
        flags = result.fetchall()
        assert len(descriptions) > 0
        assert len(flags) > 0

    def test_update_should_not_span_warnings_when_all_schemas_are_not_updated(self, caplog):
        caplog.set_level(logging.WARNING)
        # updating report schema not allowed
        dop.update_db_object_properties(self.engine, ['store'])
        assert len(caplog.record_tuples) == 0
