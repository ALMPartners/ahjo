from contextlib import contextmanager
from os import chdir, getcwd
from subprocess import PIPE, Popen

import pytest
import logging

import ahjo.operations.tsql.db_object_properties as dop

EXT_PROP_QUERY = """
    SELECT CAST(value as VARCHAR(8000))
    FROM sys.extended_properties
    WHERE name = 'Description' AND value != ''"""


@contextmanager
def temporal_cwd(path):
    oldpwd = getcwd()
    chdir(path)
    try:
        yield
    finally:
        chdir(oldpwd)


@pytest.mark.mssql
class TestWithSQLServer():

    @pytest.fixture(scope='function', autouse=True)
    def db_objects_setup_and_teardown(self, mssql_sample, mssql_engine):
        self.engine = mssql_engine
        self.cwd = mssql_sample
        p = Popen(['ahjo', 'deploy-without-git-version-and-object-properties', 'config_development.jsonc'],
                  cwd=mssql_sample, stdin=PIPE)
        p.communicate(input='y\n'.encode())
        yield
        p = Popen(['ahjo', 'downgrade', 'config_development.jsonc'],
                  cwd=mssql_sample, stdin=PIPE)
        p.communicate(input='y\n'.encode())

    def test_objects_should_not_have_descriptions_before_update(self):
        result = self.engine.execute(EXT_PROP_QUERY)
        descriptions = result.fetchall()
        assert len(descriptions) == 0

    def test_objects_should_have_descriptions_after_update(self):
        with temporal_cwd(self.cwd):
            dop.update_db_object_properties(self.engine, ['store', 'report'])
        result = self.engine.execute(EXT_PROP_QUERY)
        descriptions = result.fetchall()
        assert len(descriptions) > 0

    def test_update_should_not_span_warnings_when_all_schemas_are_not_updated(self, caplog):
        caplog.set_level(logging.WARNING)
        with temporal_cwd(self.cwd):
            # updating report schema not allowed
            dop.update_db_object_properties(self.engine, ['store'])
        assert len(caplog.record_tuples) == 0
